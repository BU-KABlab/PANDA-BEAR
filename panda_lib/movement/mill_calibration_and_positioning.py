"""
This module contains functions for calibrating and positioning a mill, wellplate, and vials.

The functions in this module allow the user to:
 - check and change mill settings
 - calibrate the locations of individual wells in a wellplate
 - calibrate the z_bottom of the wellplate to the mill

The module relies on other modules such as:
    - `mill_control`
    - `utilities`
    - `vials`
    - `wellplate`
    - `config`
"""

import logging

# pylint: disable=unused-argument
import os
import platform
from typing import Sequence

from panda_lib.config.config_tools import read_config
from panda_lib.experiment_class import ExperimentResultsRecord, insert_experiment_result
from panda_lib.imaging import capture_new_image, image_filepath_generator
from panda_lib.log_tools import setup_default_logger
from panda_lib.utilities import Coordinates as WellCoordinates
from panda_lib.utilities import Instruments, input_validation
from panda_lib.vials import StockVial, WasteVial
from panda_lib.wellplate import Well, Wellplate

from panda_lib.grlb_mill_wrapper import (
    PandaMill as Mill,
    MockPandaMill as MockMill,
    Tool,
    Coordinates,
)

logger = setup_default_logger(log_name="mill_config", console_level=logging.DEBUG)


config = read_config()["MILL"]


def check_mill_settings(mill: Mill, *args, **kwargs):
    """
    Fetch the settings list from the grbl controller and compare to the settings file.
    If there are differences, ask the user if they would like to change the settings.
    If so, ask for the settings to change and the new value.
    Update the settings file and send the new setting to the mill.
    Confirm the setting has been applied and save the settings file.
    Repeat until the user is satisfied.
    """

    # mill settings
    update_grbl_settings(mill)
    # instrument offsets
    update_instrument_offsets(mill)
    # add or remove an instrument
    manage_instruments(mill)
    # working volume
    update_working_volume(mill)
    # electrode bath
    update_electrode_bath(mill)
    # safe floor height
    update_safe_floor_height(mill)


def update_grbl_settings(mill: Mill, *args, **kwargs):
    """
    Fetch the settings list from the grbl controller and compare to the settings file.
    If there are differences, ask the user if they would like to change the settings.
    If so, ask for the settings to change and the new value.
    Update the settings file and send the new setting to the mill.
    Confirm the setting has been applied and save the settings file.
    Repeat until the user is satisfied.
    """
    while True:
        response = mill.execute_command("$$")  # Get grlb settings
        if response is None:
            logger.error("Error fetching grbl settings")
            break

        # Check grbl settings
        settings: dict = mill.config["settings"]
        # List out grbl settings and note any differences.
        print("\nCurrent grbl settings:")
        for setting, value in response.items():
            if str(settings.get(setting)) != value:
                print(
                    f"Setting {setting:<4} | Current: {value:<10}, Config: {settings.get(setting):<5}"
                )
            else:
                print(f"Setting {setting:<4} | Current: {value:<10}")

        # Ask if user wants to change settings
        change_settings = input("Would you like to change any grbl settings? (y/n): ")
        if change_settings.lower() in ["y", "yes", ""]:
            while True:
                # Ask for setting to change
                setting_to_change = input(
                    "Enter the setting you would like to change: "
                )
                if setting_to_change not in settings:
                    print("Setting not found")
                    continue
                # Ask for the new value
                new_value = input(f"Enter the new value for {setting_to_change}: ")
                # Update loaded settings file
                settings[setting_to_change] = new_value
                mill.config["settings"] = settings

                change_settings = input(
                    "Would you like to change any other settings? (y/n): "
                )
                if change_settings.lower() in ["n", "no"]:
                    break

            # Send the new settings to the mill
            for setting, value in settings.items():
                mill.execute_command(f"{setting}={value}")
            # Confirm settings have been applied
            response = mill.execute_command("$$")  # Get settings
            if response == settings:
                print("Settings have been applied")
                # Save the settings file
                mill.config["settings"] = settings
                mill.save_config()
                break
            else:
                mill.fetch_saved_config()  # Reset the settings to the last saved settings
                print("Settings have not been applied")
                try_again = input("Would you like to try again? (y/n): ")
                if try_again.lower() in ["n", "no"]:
                    break
        else:
            break


def update_instrument_offsets(mill: Mill, *args, **kwargs):
    """
    Fetch the instrument offsets from the mill instance, and ask the user if they
    would like to change the settings.
    If so, ask for the instrument to change and the new value.
    Update the settings file and send the new setting to the mill instance.
    Confirm the setting has been applied and save the settings file.
    Repeat until the user is satisfied.
    """
    # Review the instrument offset settings
    instrument_offsets: dict = mill.config["instrument_offsets"]
    print("\nCurrent instrument offsets:")
    for instrument, offset in instrument_offsets.items():
        print(f"{instrument}: {offset}")

    # Ask if user wants to change instrument offsets
    change_instrument_offsets = input(
        "\nWould you like to change any instrument offsets? (y/n): "
    )
    if change_instrument_offsets.lower() in ["y", "yes", ""]:
        while True:
            instrument_to_change = input_validation(
                "Enter the instrument you would like to change: ",
                str,
                menu_items=list(instrument_offsets.keys()),
            )

            if instrument_to_change not in instrument_offsets:
                print("Instrument not found")
                continue

            new_coordinates = {}
            for coordinate in ["x", "y", "z"]:
                while True:  # Validation loop
                    new_coordinate = input(
                        f"Enter the new {coordinate.upper()} coordinate for the {instrument_to_change} or enter for no change: "
                    )
                    if new_coordinate != "":
                        try:
                            new_coordinates[coordinate] = float(new_coordinate)
                            break
                        except ValueError:
                            print("Invalid input, please try again")
                            continue
                    else:  # If the user enters nothing, keep the current value
                        new_coordinates[coordinate] = instrument_offsets[
                            instrument_to_change
                        ][coordinate]
                        break

            instrument_offsets[instrument_to_change] = new_coordinates

            # Save the updated instrument offsets to the config file
            mill.config["instrument_offsets"] = instrument_offsets
            mill.save_config()

            mill.fetch_saved_config()  # Update the mill with the new settings
            # Check that the changed instrument offsets match the new settings
            # If they do not, ask the user if they would like to try again
            response = mill.config["instrument_offsets"][instrument_to_change]
            if (
                response["x"] == new_coordinates["x"]
                and response["y"] == new_coordinates["y"]
                and response["z"] == new_coordinates["z"]
            ):
                print(f"{instrument_to_change} has been updated to {response}")
            else:
                print(f"{instrument_to_change} has not been updated")
                try_again = input("Would you like to try again? (y/n): ")
                if try_again.lower() in ["y", "yes", ""]:
                    continue

            change_instrument_offsets = input(
                "Would you like to change any other instrument offsets? (y/n): "
            )
            if change_instrument_offsets.lower() in ["n", "no"]:
                break


def manage_instruments(mill: Mill, *args, **kwargs):
    """
    Add or remove an instrument from the mill
    """
    # Display the current instruments
    instruments: dict = mill.config["instrument_offsets"]
    print("\nCurrent instruments:")
    for instrument in instruments:
        print(instrument)

    while True:
        modify_instruments = input(
            "Would you like to add or remove an instrument? (add/remove/done): "
        )
        if modify_instruments.lower() in ["add", "a", ""]:
            new_instrument = input("Enter the name of the new instrument: ")
            instruments[new_instrument] = {"x": 0, "y": 0, "z": 0}
            mill.config["instrument_offsets"] = instruments
            mill.save_config()
            print(f"{new_instrument} has been added to the instruments")
            change_new_instrument_offset = input(
                "Would you like to change the offset for the new instrument? (y/n): "
            )
            if change_new_instrument_offset.lower() in ["y", "yes", ""]:
                new_coordinates = {}
                for coordinate in ["x", "y", "z"]:
                    while True:
                        new_coordinate = input(
                            f"Enter the new {coordinate.upper()} coordinate for the {new_instrument} or enter for no change: "
                        )
                        if new_coordinate != "":
                            try:
                                new_coordinates[coordinate] = float(new_coordinate)
                                break  # exit new instrument offset loop
                            except ValueError:
                                print("Invalid input, please try again")
                                continue
                        else:
                            new_coordinates[coordinate] = 0
                            break  # exit new instrument offset loop

                instruments[new_instrument] = new_coordinates
                mill.config["instrument_offsets"] = instruments
                mill.save_config()
        elif modify_instruments.lower() in ["remove", "r"]:
            while True:
                remove_instrument = input(
                    "Enter the name of the instrument to remove (or 'back' to go back): "
                )
                if remove_instrument.lower() == "back":
                    break  # exit remove instrument loop
                if remove_instrument in instruments:
                    instruments.pop(remove_instrument)
                    mill.config["instruments"] = instruments
                    mill.save_config()
                    print(f"{remove_instrument} has been removed from the instruments")
                    break  # exit remove instrument loop
                print("Instrument not found")
                continue  # continue remove instrument loop
        else:
            break  # exit modify instruments loop


def update_working_volume(mill: Mill, *args, **kwargs):
    """
    Update the working volume of the mill
    """
    # Display the working volume
    working_volume = mill.config["working_volume"]
    print(f"Current working volume: {working_volume}")

    while True:  # Loop to modify the working volume
        modify_working_volume = input(
            "Would you like to change the working volume? (y/n): "
        )
        if modify_working_volume.lower() in ["y", "yes", ""]:
            new_working_volume = {}
            for coordinate in ["x", "y", "z"]:
                while True:  # Validation loop
                    new_coordinate = input(
                        f"Enter the new {coordinate.upper()} coordinate for the working volume or enter for no change: "
                    )
                    if new_coordinate != "":
                        try:
                            new_working_volume[coordinate] = float(new_coordinate)
                            break
                        except ValueError:
                            print("Invalid input, please try again")
                            continue
                    else:
                        new_working_volume[coordinate] = working_volume[coordinate]
                        break

            mill.config["working_volume"] = new_working_volume
            mill.save_config()

            print(f"New working volume: {working_volume}")
        else:
            break


def update_electrode_bath(mill: Mill, *args, **kwargs):
    """
    Update the location of the electrode bath
    """
    # Show the location of the electrode bath
    electrode_bath = mill.config["electrode_bath"]
    print(f"Current electrode bath location: {electrode_bath}")
    modify_electrode_bath = input(
        "Would you like to change the electrode bath location? (y/n): "
    )
    if modify_electrode_bath.lower() in ["y", "yes", ""]:
        new_coordinates = {}
        for coordinate in ["x", "y", "z"]:
            new_coordinate = input_validation(
                f"Enter the new {coordinate.upper()} coordinate for the electrode bath or enter for no change: ",
                float,
                (-400, 1),
                True,
            )
            if new_coordinate is not None:
                new_coordinates[coordinate] = new_coordinate
                break

            else:
                new_coordinates[coordinate] = electrode_bath[coordinate]

        electrode_bath = new_coordinates

        mill.config["electrode_bath"] = electrode_bath
        mill.save_config()

        print(f"New electrode bath location: {electrode_bath}")


def update_safe_floor_height(mill: Mill, *args, **kwargs):
    """
    Update the safe floor height of the mill
    """
    # Show the safe floor height
    safe_floor_height = mill.config["safe_height_floor"]
    print(f"Current safe floor height: {safe_floor_height}")
    while True:
        change_safe_floor_level = input(
            "Would you like to change the safe floor height? (y/n): "
        )
        if change_safe_floor_level.lower() == "y":
            new_safe_floor_height = input_validation(
                "Enter the new safe floor height or enter for no change: ",
                float,
                (-80, 1),
            )
            if not new_safe_floor_height:
                new_safe_floor_height = safe_floor_height

            mill.config["safe_height_floor"] = new_safe_floor_height
            mill.save_config()

            print(f"New safe floor height: {safe_floor_height}")
        else:
            break


def calibrate_wells(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """
    Calibrate the locations of the individual wells in the wellplate using either
    the pipette or the electrode.
    This will set the x and y coordinates of ONLY the selected wells, leaving
    the rest unchanged, unless the user chooses to recalculate all well locations.
    This is useful for when a single well is off and needs to be corrected.

    Args:
        mill (Mill)
        wellplate (Wellplate)

    """
    # Enter well choice loop
    instrument = "pipette"
    while True:
        coordinates_changed = False
        well_id = input(
            "Enter the well ID to test (e.g., A1) toggle to switch to electrode or done to end: "
        ).lower()
        if well_id == "done":
            break

        if well_id == "toggle":
            instrument = "electrode" if instrument == "pipette" else "pipette"
            print(f"Instrument has been toggled to {instrument}")
            well_id = input("Enter the well ID to test (e.g., A1): ").lower()

        # Ensure that the well_id is valid
        if well_id.upper() not in wellplate.wells:
            print("Invalid well ID")
            continue

        # Provide the current coordinates of the well
        original_coordinates = wellplate.get_coordinates(well_id)
        print(f"Current coordinates of {well_id}: {original_coordinates}")

        # Move the pipette to the top of the well
        mill.safe_move(
            coordinates=Coordinates(
                original_coordinates["x"], original_coordinates["y"], wellplate.top
            ),
            tool=instrument,
        )

        # Enter confirmation loop
        while True:
            current_coorinates = Coordinates(
                original_coordinates["x"],
                original_coordinates["y"],
                wellplate.top,
            )
            confirm = input(
                f"Is the {(instrument)}  in the correct position? (yes/no): "
            )
            if confirm is None or confirm.lower().strip()[0] in ["y", ""]:
                break  # exit confirmation loop go to updating coordinates if changed
            print(
                f"Current coordinates of {well_id}: {current_coorinates}"
            )  # change to be the corrected coordinates if they have been changed
            coordinates_changed = True
            # gather new coordinates and test them for validity before trying to set them
            # enter validation loop
            while True:
                new_x = input(
                    f"Enter the new X coordinate for {well_id} or enter for no change: "
                )
                new_y = input(
                    f"Enter the new Y coordinate for {well_id} or enter for no change: "
                )

                if new_x == "":
                    new_x = original_coordinates["x"]
                if new_y == "":
                    new_y = original_coordinates["y"]
                try:
                    new_x = float(new_x)
                    new_y = float(new_y)
                except ValueError:
                    print("Invalid input, please try again")
                    continue

                working_volume = mill.config["working_volume"]
                if new_x > 0 or new_x < working_volume["x"]:
                    print(
                        f"Invalid x coordinate, must be between 0 and {working_volume['x']}"
                    )
                    continue
                if new_y > 0 or new_y < working_volume["y"]:
                    print(
                        f"Invalid y coordinate, must be between 0 and {working_volume['y']}"
                    )
                    continue
                break  # exit validation loop

            new_coordinates = Coordinates(
                new_x,
                new_y,
                wellplate.top,
            )

            # Safe move to the new coordinates
            mill.safe_move(
                coordinates=new_coordinates,
                tool=instrument,
            )

        if coordinates_changed:
            save = input("Would you like to save the new coordinates? (y/n): ")
            if save.lower() in ["y", "yes", ""]:
                if well_id.upper() == "A1":
                    recalc = input(
                        "Would you like to recalculate all well locations? (y/n): "
                    )
                    if recalc[0].lower() == "y":
                        wellplate.plate_data.a1_x = new_coordinates.x
                        wellplate.plate_data.a1_y = new_coordinates.y
                        wellplate.save()  # json file for wellplate location
                        wellplate.recalculate_well_positions()  # Update wells with new coords and depth
                else:  # Update the well with new well coordinates
                    wellplate.wells[well_id].update_coordinates(
                        new_coordinates.to_dict()
                    )


def calibrate_z_bottom_of_wellplate(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the z_bottom of the wellplate to the mill"""
    # Enter confirmation loop
    # Ask the user to enter a well id to check the z_bottom or to enter "done" to finish
    # Ask the user to confirm the pipette is in the correct position
    # If the user confirms, do nothing
    # If the user does not confirm, ask the user to input the new z_bottom
    # Safe Move to the new z_bottom
    # Repeat until the user confirms the position
    # Save the new z_bottom to the wellplate object
    # Repeat until the user enters "done"
    while True:
        well_id = (
            input("Enter a well ID to check the z_bottom or 'done' to finish: ")
            .upper()
            .strip()
        )
        if well_id in ["DONE", "d"]:
            break

        current_z_bottom = wellplate.z_bottom
        print(
            """
This calibration will move the pipette to the top of the well and give you the current z_bottom.
You will be asked to for a new z_bottom, and the pipette will move to that position.
You will be asked to accept the setting, and if you do not, you will be asked to input a new z_bottom.
              """
        )

        print(f"Current z_bottom of {well_id}: {current_z_bottom}")
        print(f"Current coordinates of {well_id}: {wellplate.get_coordinates(well_id)}")
        well = wellplate.wells[well_id]

        # Double check that the well and wellplate.wells[well_id] are the same
        assert well.coordinates == wellplate.get_coordinates(well_id)

        input("Press enter to continue...")

        mill.safe_move(
            coordinates=well.top_coordinates,
            tool="pipette",
        )
        goto = input_validation(
            "Enter a bottom to test or enter for no change: ", float, (-80, 0)
        )
        if not goto:
            goto = current_z_bottom

        current = mill.safe_move(
            coordinates=Coordinates(well.x, well.y, goto),
            tool="pipette",
        )

        while True:
            confirm = (
                input(f"Is the pipette in the correct position {current.z}? (yes/no): ")
                .lower()
                .strip()[0]
            )
            if confirm.lower() in ["y", ""]:
                break

            new_z_bottom = input_validation(
                f"Enter the new z_bottom for {well_id} (current: {current_z_bottom}): ",
                float,
                (-85, 0),
            )

            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, new_z_bottom),
                tool="pipette",
            )

        # The bottom property of wells and wellplates is a generated value so we need to update the base_thickness of the wellplate
        # The new_z_bottom is actually the z-coordinate + the base_thickness, so we will update the base_thickness according to
        # the difference between the new_z_bottom and the current z coordinate of the well.
        base_thickness = new_z_bottom - current.z
        print(f"Setting well base_thickness to: {base_thickness}")
        correct = input("Is this correct? (y/n): ")
        if correct.lower() in ["y", "yes", ""]:
            well.well_data.base_thickness = base_thickness
        else:
            print(f'How about: {current.z - new_z_bottom}?')
            correct = input("Is this correct? (y/n): ")
            if correct.lower() in ["y", "yes", ""]:
                base_thickness = current.z - new_z_bottom
                well.well_data.base_thickness = current.z - new_z_bottom
            else:
                print("Skipping well")
                continue

        well.save()

        print(f"New z_bottom for {well_id}: {well.bottom}")

        apply_to_wellplate = input("Would you like to apply this to the entire wellplate? (y/n): ")
        if apply_to_wellplate.lower() in ["y", "yes", ""]:
            wellplate.plate_data.base_thickness = base_thickness
            wellplate.save()
            wellplate.recalculate_well_positions()

        # wellplate.bottom = new_z_bottom

        # apply_to_wellplate = input(
        #     "Would you like to apply this to the entire wellplate? (y/n): "
        # )
        # if apply_to_wellplate.lower() in ["y", "yes", ""]:
        #     wellplate.bottom = new_z_bottom
        #     wellplate.top = new_z_bottom + wellplate.height
        #     for well in wellplate.wells:
        #         well_obj: Well = wellplate.wells[well]
        #         well_obj.depth = new_z_bottom
        #         well_obj.height = new_z_bottom + well_obj.height
        #         # We do this instead of recalculating every well location incase
        #         # they are uniquely located in x and y
        #         # We are assuming the z_bottom is the same for all wells
        #         wellplate.write_wellplate_location()  # json file for wellplate location
        #         wellplate.recalculate_well_locations()  # Update wells with new coords and depth
        # else:
        #     wellplate.update_well_coordinates(
        #         well_id,
        #         WellCoordinates(
        #             x=wellplate.get_coordinates(well_id, "x"),
        #             y=wellplate.get_coordinates(well_id, "y"),
        #             z_bottom=new_z_bottom,
        #             z_top=new_z_bottom + wellplate.height,
        #         ),
        #     )


def calibrate_echem_height(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the height for the echem"""
    # Move the pipette to the top of the wellplate
    response = input(
        "Electrode will move to 0 above A1. Press enter to proceed or 'q' to quit: "
    )
    if response.lower() == "q":
        return

    mill.safe_move(
        wellplate.get_coordinates("A1", "x"),
        wellplate.get_coordinates("A1", "y"),
        0,
        Instruments.ELECTRODE,
    )

    print(f"Current echem height is set to: {wellplate.echem_height}")

    # Set a new echem height?
    new_echem_height = input(
        "Would you like to set a new echem height? (y/n): "
    ).lower()
    if new_echem_height in ["y", "yes", ""]:
        while True:
            new_echem_height = input_validation(
                "Enter the new echem height or enter for no change: ", float, (-80, 0)
            )

            current = mill.safe_move(
                wellplate.get_coordinates("A1", "x"),
                wellplate.get_coordinates("A1", "y"),
                new_echem_height,
                Instruments.ELECTRODE,
            )

            response = input(
                f"Is the echem in the correct position at {current.z}? (yes/no): "
            ).lower()

            if response in ["y", "yes", ""]:
                break

        if new_echem_height is not None:
            wellplate.echem_height = new_echem_height
            wellplate.write_wellplate_location()
            print(f"New echem height: {wellplate.echem_height}")


def calibrate_vials(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the vials to the mill"""
    # Enter vial choice loop
    # ask the user for the vial position they would like to test, must be in the form of [vV][1-16]
    # Provide the current coordinates of the vial
    # Move the pipette to the top of the vial
    # Enter confirmation loop
    # Ask the user to confirm the pipette is in the correct position
    # If the user confirms, do nothing
    # Else ask the user to input the new coordinates (display current coordinates)
    # Safe Move to the new coordinates
    # Repeat until the user confirms the position
    # Save the new coordinates to the stock vial object
    # Repeat until the user enters "done"
    # Enter vial z_bottom loop
    # Enter confirmation loop
    # Ask the user to enter a vial position to check the z_bottom or to enter "done" to finish
    # Ask the user to confirm the pipette is in the correct position
    # If the user confirms, do nothing
    # If the user does not confirm, ask the user to input the new z_bottom
    # Safe Move to the new z_bottom
    # Repeat until the user confirms the position
    # Save the new z_bottom to the stock vial object

    ## Calibrate the waste vial
    # Same process as the stock vials


def calibrate_camera_focus(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the camera focus"""
    # Move the camera to the top of the wellplate
    response = input(
        "Camera will move to image_height above A1. Press enter to proceed or 'q' to quit: "
    )
    if response.lower() == "q":
        return
    mill.safe_move(
        wellplate.get_coordinates("A1", "x"),
        wellplate.get_coordinates("A1", "y"),
        wellplate.image_height,
        Instruments.LENS,
    )

    print(f"Current image height: {wellplate.image_height}")

    # Set a new image height?
    new_image_height = input(
        "Would you like to set a new image height? (y/n): "
    ).lower()
    if new_image_height in ["y", "yes", ""]:
        while True:
            new_image_height = input_validation(
                "Enter the new image height or enter for no change: ", float, (-80, 0)
            )

            current = mill.safe_move(
                wellplate.get_coordinates("A1", "x"),
                wellplate.get_coordinates("A1", "y"),
                new_image_height,
                Instruments.LENS,
            )

            response = input(
                f"Is the camera in the correct position at {current.z}? (yes/no): "
            ).lower()

            if response in ["y", "yes", ""]:
                break

        if new_image_height is not None:
            wellplate.image_height = new_image_height
            wellplate.write_wellplate_location()
            print(f"New image height: {wellplate.image_height}")


def capture_well_photo_manually(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """
    Capture a photo of a well manually

    Asks the user to input the well ID to capture a photo of.
    Also asks for relevant experiment id, project id, campaign id, and context.
    Experiment id is an integer: 1000000 <= experiment_id <= 9999999
    Project id and campaign id are integers.
    Context is one of these strings: 'BeforeDeposition', 'AfterBleaching', 'AfterColoring'

    Future versions will use the experiment id, to look up the project, campaign ids.

    """

    while True:
        well_id = (
            input("Enter the well ID to capture a photo of (e.g., A1): ")
            .upper()
            .strip()
        )
        experiment_id = int(input("Enter the experiment ID: "))
        project_id = int(input("Enter the project ID: "))
        campaign_id = int(input("Enter the campaign ID: "))
        context = input(
            "Enter the context (BeforeDeposition, AfterBleaching, AfterColoring): "
        ).strip()

        # lower to the wellplate's image height
        mill.safe_move(
            wellplate.get_coordinates(well_id, "x"),
            wellplate.get_coordinates(well_id, "y"),
            wellplate.image_height,
            Instruments.LENS,
        )
        # pause for the user to focus the camera
        input(
            "Focus the camera using FlyCapture2 if necessary and press enter to continue"
        )

        # Capture the image
        image_path = image_filepath_generator(
            exp_id=experiment_id,
            project_id=project_id,
            project_campaign_id=campaign_id,
            well_id=well_id,
            step_description=context,
        )

        capture_new_image(save=True, num_images=1, file_name=image_path)

        view_image = input("Would you like to view the image? (y/n): ")
        if view_image.lower() == "y":
            if platform.system() == "Windows":
                os.system(f"start {image_path}")
            elif platform.system() == "Darwin":
                os.system(f"open {image_path}")
            elif platform.system() == "Linux":
                os.system(f"xdg-open {image_path}")
            else:
                print("Unsupported OS")

        save_to_db = input("Would you like to save the image to the database? (y/n): ")
        if save_to_db.lower() != "y":
            pass
        else:
            # Save the image path to the database
            insert_experiment_result(
                ExperimentResultsRecord(
                    experiment_id=experiment_id,
                    result_type="image",
                    result_value=str(image_path),
                    context=context,
                )
            )

        to_continue = input("Would you like to capture another image? (y/n): ")
        if to_continue.lower() == "n":
            return  # exit the loop


def home_mill(mill: Mill, *args, **kwargs):
    """Homes the mill"""
    mill.home()
    print("Mill has been homed")


def quit_calibration():
    """Quit the calibration menu"""
    print("Quitting calibration menu")
    return


menu_options = {
    "0": check_mill_settings,
    "1": home_mill,
    "3": calibrate_wells,
    "4": calibrate_z_bottom_of_wellplate,
    "5": calibrate_echem_height,
    "6": calibrate_camera_focus,
    "7": capture_well_photo_manually,
    "q": quit_calibration,
}


def calibrate_mill(
    use_mock_mill: bool,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the mill to the wellplate and stock vials"""
    if not use_mock_mill:
        mill = Mill
    else:
        mill = MockMill

    # Connect to the mill
    with mill() as cncmill:
        while True:
            # os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
            print("\n\n")
            print("""\nWelcome to the mill calibration and positioning menu:""")
            for key, value in menu_options.items():
                print(f"{key}. {value.__name__.replace('_', ' ').title()}")
            option = input("Which operation would you like: ")
            if option == "q":
                # cncmill.rest_electrode()
                break
            menu_options[option](cncmill, wellplate, stock_vials, waste_vials)


def main():
    """Main function for testing the calibration functions"""
    # Load the configuration file
    testing = input("Enter 'y' to use testing configuration: ").lower() == "y"
    if testing == "y":
        testing = True
    else:
        testing = False
    from panda_lib.vials import read_vials

    print("Testing mode:", testing)
    input("Press enter to continue")

    # Create the wellplate object
    wellplate_to_use = Wellplate()

    # Create the stock vial objects
    stock_vials_to_use: Sequence[StockVial] = read_vials()[0]
    waste_vials_to_use: Sequence[WasteVial] = read_vials()[1]

    calibrate_mill(True, wellplate_to_use, stock_vials_to_use, waste_vials_to_use)


if __name__ == "__main__":
    main()
