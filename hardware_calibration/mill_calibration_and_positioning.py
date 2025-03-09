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
import os
import platform
from pathlib import Path
from typing import Sequence

from panda_lib.imaging import capture_new_image
from panda_lib.labware.vials import StockVial, Vial, WasteVial, read_vials
from panda_lib.labware.wellplates import Well, Wellplate
from panda_lib.panda_gantry import Coordinates
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.utilities import Instruments, input_validation
from shared_utilities.config.config_tools import read_config
from shared_utilities.log_tools import setup_default_logger

from .decapper_testing import main as decapper_test

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
    update_grbl_settings(mill)
    update_instrument_offsets(mill)
    manage_instruments(mill)
    update_working_volume(mill)
    update_electrode_bath(mill)


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
        response = mill.grbl_settings()  # Get grbl settings
        if response is None:
            logger.error("Error fetching grbl settings")
            break

        settings = mill.config
        print("\nCurrent grbl settings:")
        for setting, value in response.items():
            if str(settings.get(setting)) != value:
                print(
                    f"Setting {setting:<4} | Current: {value:<10}, Config: {settings.get(setting):<5}"
                )
            else:
                print(f"Setting {setting:<4} | Current: {value:<10}")

        change_settings = input("Would you like to change any grbl settings? (y/n): ")
        if change_settings.lower() in ["y", "yes", ""]:
            while True:
                setting_to_change = input(
                    "Enter the setting you would like to change: "
                )
                if setting_to_change not in settings:
                    if "$" + setting_to_change in settings:
                        setting_to_change = "$" + setting_to_change
                    else:
                        print("Setting not found")
                        continue
                new_value = input(f"Enter the new value for {setting_to_change}: ")
                settings[setting_to_change] = new_value
                mill.config = settings

                if input(
                    "Would you like to change any other settings? (y/n): "
                ).lower() in ["n", "no"]:
                    break

            for setting, value in settings.items():
                mill.execute_command(f"{setting}={value}")

            response = mill.grbl_settings()
            if response == settings:
                print("Settings have been applied")
                mill.write_mill_config_file()
                break
            else:
                mill.read_mill_config_file()
                print("Settings have not been applied")
                if input("Would you like to try again? (y/n): ").lower() in ["n", "no"]:
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
    tool_manager = mill.tool_manager
    print("\nCurrent instrument offsets:")
    for tool_name, tool_offset in tool_manager.tool_offsets.items():
        print(f"{tool_name}: {tool_offset}")

    if input("\nWould you like to change any instrument offsets? (y/n): ").lower() in [
        "y",
        "yes",
        "",
    ]:
        while True:
            tool_name = input_validation(
                "Enter the instrument you would like to change: ",
                str,
                menu_items=list(tool_manager.tool_offsets.keys()),
            )
            if tool_name not in tool_manager.tool_offsets:
                print("Instrument not found")
                continue

            new_coordinates = {}
            for coordinate in ["x", "y", "z"]:
                new_coordinate = input(
                    f"Enter the new {coordinate.upper()} coordinate for the {tool_name} or enter for no change: "
                )
                if new_coordinate != "":
                    try:
                        new_coordinates[coordinate] = float(new_coordinate)
                    except ValueError:
                        print("Invalid input, please try again")
                        continue
                else:
                    new_coordinates[coordinate] = getattr(
                        tool_manager.tool_offsets[tool_name].offset, coordinate
                    )

            tool_manager.update_tool(tool_name, Coordinates(**new_coordinates))
            mill.write_mill_config_file()

            if input(
                "Would you like to change any other instrument offsets? (y/n): "
            ).lower() in ["n", "no"]:
                break


def manage_instruments(mill: Mill, *args, **kwargs):
    """
    Add or remove an instrument from the mill
    """
    tool_manager = mill.tool_manager
    print("\nCurrent instruments:")
    for tool_name in tool_manager.tool_offsets:
        print(tool_name)

    while True:
        action = input(
            "Would you like to add or remove an instrument? (add/remove/done): "
        ).lower()
        if action in ["add", "a", ""]:
            tool_name = input("Enter the name of the new instrument: ")
            tool_manager.add_tool(tool_name, Coordinates(0, 0, 0))
            print(f"{tool_name} has been added to the instruments")
            if input(
                "Would you like to change the offset for the new instrument? (y/n): "
            ).lower() in ["y", "yes", ""]:
                update_instrument_offsets(mill)
        elif action in ["remove", "r"]:
            tool_name = input(
                "Enter the name of the instrument to remove (or 'back' to go back): "
            ).lower()
            if tool_name == "back":
                break
            if tool_name in tool_manager.tool_offsets:
                tool_manager.delete_tool(tool_name)
                print(f"{tool_name} has been removed from the instruments")
            else:
                print("Instrument not found")
        else:
            break


def update_working_volume(mill: Mill, *args, **kwargs):
    """
    Update the working volume of the mill
    """
    pass
    # working_volume = mill.config["working_volume"]
    # print(f"Current working volume: {working_volume}")

    # if input("Would you like to change the working volume? (y/n): ").lower() in [
    #     "y",
    #     "yes",
    #     "",
    # ]:
    #     new_working_volume = {}
    #     for coordinate in ["x", "y", "z"]:
    #         new_coordinate = input(
    #             f"Enter the new {coordinate.upper()} coordinate for the working volume or enter for no change: "
    #         )
    #         if new_coordinate != "":
    #             try:
    #                 new_working_volume[coordinate] = float(new_coordinate)
    #             except ValueError:
    #                 print("Invalid input, please try again")
    #                 continue
    #         else:
    #             new_working_volume[coordinate] = working_volume[coordinate]

    #     mill.config["working_volume"] = new_working_volume
    #     mill.write_mill_config_file()
    #     print(f"New working volume: {working_volume}")


def update_electrode_bath(mill: Mill, *args, **kwargs):
    """
    Update the location of the electrode bath using the vial object
    """

    electrode_bath_vial = Vial("e1")
    electrode_bath_coordinates = electrode_bath_vial.coordinates
    print(f"Current electrode bath location: {electrode_bath_coordinates}")

    if input(
        "Would you like to change the electrode bath location? (y/n): "
    ).lower() in ["y", "yes", ""]:
        new_coordinates = Coordinates(0, 0, 0)
        for coordinate in ["x", "y", "z"]:
            new_coordinate = input_validation(
                f"Enter the new {coordinate.upper()} coordinate for the electrode bath or enter for no change: ",
                float,
                (-400, 1),
                True,
            )
            if new_coordinate is not None:
                new_coordinates[coordinate] = new_coordinate
            else:
                new_coordinates[coordinate] = electrode_bath_coordinates[coordinate]

        electrode_bath_vial.vial_data.coordinates = new_coordinates.to_dict()
        electrode_bath_vial.save()
        print(f"New electrode bath location: {new_coordinates}")


def calibrate_wells(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """
    Calibrate the locations of the individual wells in the wellplate using either
    the pipette or the electrode.
    This will set the x and y coordinates of ONLY the selected wells, leaving
    the rest unchanged, unless the user chooses to recalculate all well locations.
    This is useful for when a single well is off and needs to be corrected.
    """
    instrument = "pipette"

    print("\n=== Wellplate XY Position Calibration ===")
    print("This will help you calibrate the X-Y positions of individual wells.")
    print("The instrument will move to the top of each selected well.")

    while True:
        # Step 1: Select a well or change instrument
        well_id = (
            input(
                f"\nCurrent instrument: {instrument}\n"
                "Enter well ID to calibrate (e.g., A1), 'toggle' to switch instruments, "
                "or 'done' to finish: "
            )
            .upper()
            .strip()
        )

        if well_id == "DONE":
            break

        if well_id == "TOGGLE":
            instrument = "electrode" if instrument == "pipette" else "pipette"
            print(f"Instrument has been toggled to {instrument}")
            continue

        if well_id not in wellplate.wells:
            print("Invalid well ID. Please try again.")
            continue

        # Step 2: Move to the well and display current position
        well = wellplate.wells[well_id]
        original_coordinates = well.top_coordinates
        print(f"\nCurrent settings for {well_id}:")
        print(f"  - X coordinate: {original_coordinates.x}")
        print(f"  - Y coordinate: {original_coordinates.y}")
        print(f"  - Z top: {wellplate.top}")

        # Step 3: Move to the well
        print(f"\nMoving {instrument} to the top of well {well_id}...")
        mill.safe_move(
            coordinates=original_coordinates,
            tool=instrument,
        )

        # Step 4: Check if position needs adjustment
        position_correct = (
            input(
                f"\nIs the {instrument} positioned correctly above well {well_id}? (y/n): "
            )
            .lower()
            .strip()
        )

        if position_correct in ["y", "yes", ""]:
            continue

        # Step 5: Position is not correct, get new coordinates

        # Step 6: Get new X coordinate
        new_x = input_validation(
            "Enter new X coordinate or enter for no change: ",
            (int, float),
            (mill.working_volume.x, 0),
            allow_blank=True,
            default=original_coordinates.x,
        )
        if new_x == "":
            new_x = original_coordinates.x

        # Step 7: Get new Y coordinate
        new_y = input_validation(
            "Enter new Y coordinate or enter for no change: ",
            (int, float),
            (mill.working_volume.y, 0),
            allow_blank=True,
            default=original_coordinates.y,
        )
        if new_y == "":
            new_y = original_coordinates.y

        # Convert to appropriate types
        try:
            new_x = float(new_x)
            new_y = float(new_y)
        except ValueError:
            print("Invalid input. Using original coordinates.")
            new_x, new_y = original_coordinates.x, original_coordinates.y

        # Step 8: Move to new position for verification
        new_coordinates = Coordinates(new_x, new_y, wellplate.top)
        print(f"\nMoving to new coordinates: X={new_x}, Y={new_y}")
        mill.safe_move(coordinates=new_coordinates, tool=instrument)

        # Step 9: Confirm the new position
        while True:
            confirm = (
                input(
                    f"Is the {instrument} now positioned correctly above well {well_id}? (y/n): "
                )
                .lower()
                .strip()
            )

            if confirm in ["y", "yes", ""]:
                break

            # Position still not correct, get new coordinates again
            new_x = input_validation(
                "Enter new X coordinate: ",
                float,
                (mill.working_volume.x, 0),
            )
            new_y = input_validation(
                "Enter new Y coordinate: ",
                float,
                (mill.working_volume.y, 0),
            )

            new_coordinates = Coordinates(new_x, new_y, wellplate.top)
            mill.safe_move(coordinates=new_coordinates, tool=instrument)

        # Step 10: Save changes if confirmed
        save_changes = (
            input("\nSave these new coordinates for well {well_id}? (y/n): ")
            .lower()
            .strip()
        )

        if save_changes in ["y", "yes", ""]:
            # If well is A1, ask about recalculating all wells
            if well_id == "A1":
                recalculate = (
                    input(
                        "\nThis is well A1. Would you like to recalculate all well positions? (y/n): "
                    )
                    .lower()
                    .strip()
                )

                if recalculate in ["y", "yes", ""]:
                    print("Updating A1 coordinates and recalculating all wells...")
                    wellplate.plate_data.a1_x = new_coordinates.x
                    wellplate.plate_data.a1_y = new_coordinates.y
                    wellplate.save()
                    wellplate.recalculate_well_positions()
                    print("All well positions have been updated.")
                else:
                    # Update only this well
                    well.update_coordinates(new_coordinates)
                    print(f"Updated coordinates for well {well_id} only.")
            else:
                # For wells other than A1, just update the individual well
                well.update_coordinates(new_coordinates)
                print(f"Updated coordinates for well {well_id}.")
        else:
            print("Changes discarded.")

    print("\nWellplate XY position calibration complete.")


def calibrate_bottom_of_wellplate(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the bottom of the wellplate to the mill"""

    offset = mill.tool_manager.tool_offsets["pipette"].offset

    print("\n=== Wellplate Bottom Calibration ===")
    print("This will help you calibrate the bottom position (Z-coordinate) of wells.")

    while True:
        # Step 1: Select a well to calibrate
        well_id = (
            input("\nEnter a well ID to calibrate (e.g., A1) or 'done' to finish: ")
            .upper()
            .strip()
        )
        if well_id in ["DONE", "D"]:
            break

        if well_id not in wellplate.wells:
            print("Invalid well ID. Please try again.")
            continue

        well: Well = wellplate.wells[well_id]
        print(f"\nCurrent settings for {well_id}:")
        print(f"  - Bottom Z-coordinate: {well.bottom}")
        print(f"  - Base thickness: {well.well_data.base_thickness}")
        print(f"  - Well position: {well.coordinates}")

        # Step 2: Move to the top of the well
        print(f"\nMoving to the top of well {well_id}...")
        mill.safe_move(coordinates=well.top_coordinates, tool="pipette")

        # Step 3: Safety check before proceeding
        proceed = (
            input("\nIs it safe to proceed to test the well bottom? (y/n/q): ")
            .lower()
            .strip()
        )
        if proceed == "q":
            break
        if proceed not in ["y", "yes", ""]:
            print("Skipping this well.")
            continue

        # Step 4: Ask if user wants to test current bottom or specify a new test value
        use_current = (
            input(f"\nDo you want to test the current bottom ({well.bottom})? (y/n): ")
            .lower()
            .strip()
        )
        if use_current in ["y", "yes", ""]:
            test_bottom = well.bottom
        else:
            test_bottom = input_validation(
                "Enter a bottom Z-coordinate to test: ", float, (-200, 0)
            )
            if test_bottom is None:
                test_bottom = well.bottom

        # Step 5: Move to the test bottom position
        print(f"\nMoving to test bottom position: Z = {test_bottom}")
        current = mill.safe_move(
            coordinates=Coordinates(well.x, well.y, test_bottom), tool="pipette"
        )

        # Step 6: Iteratively adjust the bottom position until correct
        while True:
            is_correct = (
                input("\nIs the pipette at the correct bottom position? (y/n): ")
                .lower()
                .strip()
            )

            if is_correct in ["y", "yes", ""]:
                break

            test_bottom = input_validation(
                "Enter a new bottom Z-coordinate to test: ", float, (-200, 0)
            )

            if test_bottom is None:
                print("Invalid input. Keeping current position.")
                continue

            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, test_bottom), tool="pipette"
            )

        # Step 7: Calculate base thickness from final position
        final_z = current.z - offset.z  # Adjust for tool offset
        base_thickness = abs(final_z - well.z)
        print(f"\nCalculated base thickness: {base_thickness} mm")

        # Step 8: Confirm and save changes
        save_changes = (
            input("Save this base thickness for this well? (y/n): ").lower().strip()
        )
        if save_changes in ["y", "yes", ""]:
            well.well_data.base_thickness = base_thickness
            well.save()
            print(
                f"Updated well {well_id} with new base thickness: {base_thickness} mm"
            )
            print(f"New bottom Z-coordinate for {well_id}: {well.bottom}")

            # Step 9: Optionally apply to the entire wellplate
            apply_all = (
                input(
                    "\nApply this base thickness to ALL wells in the wellplate? (y/n): "
                )
                .lower()
                .strip()
            )

            if apply_all in ["y", "yes", ""]:
                wellplate.plate_data.base_thickness = base_thickness
                wellplate.save()
                wellplate.recalculate_well_positions()
                print(f"Updated wellplate with base thickness: {base_thickness} mm")
        else:
            print("Changes discarded.")

    print("\nWellplate bottom calibration complete.")


def calibrate_echem_height(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the height for electrochemical measurements"""

    print("\n=== Electrochemical Height Calibration ===")
    print("This will help you calibrate the height for electrochemical measurements.")
    print(
        "The electrode will be positioned at the correct height above the well bottom."
    )

    # Step 1: Initial confirmation
    response = (
        input(
            "\nThe electrode will move to well A1. Press enter to proceed or 'q' to quit: "
        )
        .lower()
        .strip()
    )
    if response == "q":
        return

    # Step 2: Move to the reference well (A1)
    well = wellplate.wells["A1"]
    offset = mill.tool_manager.tool_offsets["electrode"].offset

    print("\nMoving electrode to the top of well A1...")
    mill.safe_move(coordinates=well.top_coordinates, tool="electrode")

    # Step 3: Display current settings
    print("\nCurrent echem height settings:")
    print(
        f"  - Echem height offset from well bottom: {wellplate.plate_data.echem_height} mm"
    )
    print(f"  - Absolute Z-coordinate: {wellplate.echem_height}")
    print(f"  - Current mill Z-position: {mill.current_coordinates()[0].z}")

    # Step 4: Optionally test current setting
    check_current = (
        input("\nWould you like to test the current echem height? (y/n): ")
        .lower()
        .strip()
    )

    if check_current in ["y", "yes", ""]:
        print(f"\nMoving to current echem height: Z = {wellplate.echem_height}")
        current = mill.safe_move(
            coordinates=Coordinates(well.x, well.y, wellplate.echem_height),
            tool="electrode",
        )
        print(f"Positioned at Z = {current.z - offset.z} (with tool offset applied)")

    # Step 5: Ask if user wants to set a new height
    adjust_height = (
        input("\nWould you like to set a new echem height? (y/n): ").lower().strip()
    )

    if adjust_height in ["y", "yes", ""]:
        # Step 6: Iteratively adjust the height
        while True:
            # Get height offset from bottom (positive value)
            new_echem_offset = input_validation(
                "\nEnter the new height offset from the well bottom (0-10mm): ",
                float,
                (0, 10),
                allow_blank=True,
            )

            # If blank entry, keep current value
            if new_echem_offset is None:
                new_echem_height = wellplate.echem_height
                print(f"Keeping current height: {wellplate.echem_height}")
            else:
                # Calculate absolute Z value from bottom offset
                new_echem_height = well.bottom + new_echem_offset
                print(f"Setting offset to {new_echem_offset}mm above well bottom")
                print(f"This corresponds to Z-coordinate: {new_echem_height}")

            # Move to the position
            print(f"\nMoving electrode to test position: Z = {new_echem_height}")
            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, new_echem_height),
                tool="electrode",
            )

            # Check if height is correct
            is_correct = (
                input("\nIs the electrode at the correct height? (y/n): ")
                .lower()
                .strip()
            )

            if is_correct in ["y", "yes", ""]:
                break

            # If not correct, loop again to get a new value
            print("Let's try a different height.")

        # Step 7: Save the new height
        save_changes = input("\nSave this new echem height? (y/n): ").lower().strip()

        if save_changes in ["y", "yes", ""]:
            wellplate.plate_data.echem_height = new_echem_height
            wellplate.save()
            print(f"\nEchem height successfully updated to {new_echem_height}")
            print(f"This is {new_echem_height - well.bottom}mm above the well bottom")
        else:
            print("\nChanges discarded.")

    print("\nElectrochemical height calibration complete.")


def calibrate_image_height(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the height for the image"""
    print("\n=== Image Height Calibration ===")
    print("This will help you calibrate the height for taking focused images.")
    print(
        "The image height is the absolute z-coordinate for the lens when taking an image."
    )
    image_paths = []
    use_spinview = input("Are you using spinview to check the image? y/n:")
    if use_spinview.lower() == "y":
        use_spinview = True
    else:
        use_spinview = False
    response = input("Lens will move above A1. Press enter to proceed or 'q' to quit: ")
    if response.lower() == "q":
        return

    well = wellplate.wells["A1"]

    mill.safe_move(
        coordinates=Coordinates(well.x, well.y, wellplate.plate_data.image_height),
        tool="lens",
    )
    print(f"Current image height is set to: {wellplate.plate_data.image_height}")

    if not use_spinview:
        image_paths.append(take_picture_and_display())

    if input("Would you like to set a new image height? (y/n): ").lower() in [
        "y",
        "yes",
        "",
    ]:
        while True:
            new_image_height = input_validation(
                "Enter the new image height or enter for no change: ", float, (-80, 0)
            )
            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, new_image_height),
                tool=Instruments.LENS,
            )

            if not use_spinview:
                image_paths.append(take_picture_and_display())

            if input(
                f"Is the image in the correct position at {current.z}? (yes/no): "
            ).lower() in ["y", "yes", ""]:
                break

        if new_image_height is not None:
            wellplate.plate_data.image_height = new_image_height
            wellplate.save()
            print(f"New image height: {wellplate.plate_data.image_height}")

    # Clean up images taken
    for image in image_paths:
        os.remove(image)


def take_picture_and_display() -> Path:
    """
    Take a picture and display it using the appropriate system command
    """
    filepath = capture_new_image(save=True, num_images=1)
    if platform.system() == "Windows":
        os.system(f"start {filepath}")
    elif platform.system() == "Darwin":
        os.system(f"open {filepath}")
    elif platform.system() == "Linux":
        os.system(f"xdg-open {filepath}")
    else:
        print("Unsupported OS")

    return filepath


def capture_well_photo_manually(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """
    Capture a photo of a well manually

    Asks the user to input the well ID to capture a photo of.
    Also asks for relevant experiment id, project id, campaign id, and context.
    Experiment id is an integer: 1000000 <= experiment_id <= 9999999
    Project id and campaign id are integers.
    Context is one of these strings: 'BeforeDeposition', 'AfterBleaching', 'AfterColoring'
    """
    print("This function is not yet implemented")
    # TODO: Implement this function
    # while True:
    #     well_id = (
    #         input("Enter the well ID to capture a photo of (e.g., A1): ")
    #         .upper()
    #         .strip()
    #     )
    #     experiment_id = int(input("Enter the experiment ID: "))
    #     project_id = int(input("Enter the project ID: "))
    #     campaign_id = int(input("Enter the campaign ID: "))
    #     context = input(
    #         "Enter the context (BeforeDeposition, AfterBleaching, AfterColoring): "
    #     ).strip()

    #     mill.safe_move(
    #         wellplate.get_coordinates(well_id, "x"),
    #         wellplate.get_coordinates(well_id, "y"),
    #         wellplate.image_height,
    #         Instruments.LENS,
    #     )
    #     input(
    #         "Focus the camera using FlyCapture2 if necessary and press enter to continue"
    #     )

    #     image_path = image_filepath_generator(
    #         exp_id=experiment_id,
    #         project_id=project_id,
    #         project_campaign_id=campaign_id,
    #         well_id=well_id,
    #         step_description=context,
    #     )
    #     capture_new_image(save=True, num_images=1, file_name=image_path)

    #     if input("Would you like to view the image? (y/n): ").lower() == "y":
    #         if platform.system() == "Windows":
    #             os.system(f"start {image_path}")
    #         elif platform.system() == "Darwin":
    #             os.system(f"open {image_path}")
    #         elif platform.system() == "Linux":
    #             os.system(f"xdg-open {image_path}")
    #         else:
    #             print("Unsupported OS")

    #     if (
    #         input("Would you like to save the image to the database? (y/n): ").lower()
    #         == "y"
    #     ):
    #         insert_experiment_result(
    #             ExperimentResultsRecord(
    #                 experiment_id=experiment_id,
    #                 result_type="image",
    #                 result_value=str(image_path),
    #                 context=context,
    #             )
    #         )

    #     if input("Would you like to capture another image? (y/n): ").lower() == "n":
    #         return


def home_mill(mill: Mill, *args, **kwargs):
    """Homes the mill"""
    mill.home()
    print("Mill has been homed")


def quit_calibration():
    """Quit the calibration menu"""
    print("Quitting calibration menu")
    return


def calibrate_vial_holders(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    *args,
    **kwargs,
):
    """
    Calibrate the positions of vial holders. Each holder contains 8 vials spaced 33mm apart.
    The first vial (index 0) is used as reference for recalculating other positions.
    Updates can be made to individual vials or entire holders can be recalculated.
    """
    VIAL_SPACING = 33.0  # mm between vials in y-axis

    while True:
        # Select holder type
        holder_type = (
            input("\nSelect holder type to calibrate (stock/waste/done): ")
            .lower()
            .strip()
        )
        if holder_type == "done":
            break

        if holder_type not in ["stock", "waste"]:
            print("Invalid holder type")
            continue

        vials = stock_vials if holder_type == "stock" else waste_vials

        # Display current vial positions
        print(f"\nCurrent {holder_type} vial positions:")
        for i, vial in enumerate(vials):
            print(f"Vial {i}: {vial.coordinates}")

        # Select vial to calibrate
        vial_index = input_validation(
            "\nEnter vial index to calibrate or enter to skip: ",
            int,
            (0, 7),
            allow_blank=True,
        )

        if vial_index is None:
            continue

        vial: Vial = vials[vial_index]

        # Note our coodinates are funky, where the z component is currently the deck, and the actual
        # z is the bottom of the vial defined by the base thickness. In the future with the holder the
        # initial z height will come from the holder and then any wall thickness will be added to that
        original_coords = vial.coordinates
        original_bottom = vial.bottom
        print(f"\nCalibrating {holder_type} vial {vial_index}")
        print(
            f"Current coordinates: {original_coords} with the bottom at Z={original_bottom}"
        )

        # Move to the original top of vial position
        goto = Coordinates(original_coords.x, original_coords.y, vial.top)
        mill.safe_move(coordinates=goto, tool="pipette")
        # Adjust position
        new_coords = Coordinates(original_coords.x, original_coords.y, original_bottom)
        # Check if safe to proceed to bottom, if not, adjust the xy position
        new_x = None
        new_y = None

        while True:
            safe_to_proceed = input(
                "Is it safe to proceed to the bottom of the vial? (y/n): "
            ).lower()

            if safe_to_proceed not in ["y", "yes", ""]:
                new_x = input_validation(
                    "Enter new X coordinate or enter for no change: ",
                    float,
                    (mill.working_volume.x, 0),
                    allow_blank=True,
                    default=original_coords.x,
                )
                new_y = input_validation(
                    "Enter new Y coordinate or enter for no change: ",
                    float,
                    (mill.working_volume.y, 0),
                    allow_blank=True,
                    default=original_coords.y,
                )

                goto = Coordinates(new_x, new_y, vial.top)
                mill.safe_move(coordinates=goto, tool="pipette")
                continue

            break
        new_coords.x = new_x if new_x is not None else original_coords.x
        new_coords.y = new_y if new_y is not None else original_coords.y
        # Now move to the bottom of the vial
        mill.safe_move(coordinates=new_coords, tool="pipette")
        new_x, new_y, new_bottom = new_coords.x, new_coords.y, original_bottom
        # Adjust position
        while True:
            if input(
                "\nIs the pipette in the correct position? (y/n): "
            ).lower() not in ["y", "yes", ""]:
                new_x = input_validation(
                    "Enter new X coordinate or enter for no change: ",
                    float,
                    (mill.working_volume.x, 0),
                    allow_blank=True,
                    default=new_coords.x,
                )
                new_y = input_validation(
                    "Enter new Y coordinate or enter for no change: ",
                    float,
                    (mill.working_volume.y, 0),
                    allow_blank=True,
                    default=new_coords.y,
                )
                new_z = input_validation(
                    "Enter new Z coordinate or enter for no change: ",
                    float,
                    (-200, 0),
                    allow_blank=True,
                    default=original_bottom,
                )

                new_coords = Coordinates(
                    new_x if new_x is not None else new_coords.x,
                    new_y if new_y is not None else new_coords.y,
                    original_coords.z,  # We are not changing the z position here, we will change the thickness below
                )
                new_bottom = new_z if new_z is not None else original_bottom
                goto = Coordinates(new_coords.x, new_coords.y, new_bottom)
                mill.safe_move(coordinates=goto, tool="pipette")
                continue

            break

        # Save new position
        if input("\nSave new position? (y/n): ").lower() in ["y", "yes", ""]:
            vial.vial_data.coordinates = Coordinates(
                goto.x, goto.y, original_coords.z
            ).to_dict()
            # vial.vial_data.base_thickness = abs(
            #     new_bottom - original_coords.z
            # )  # Assumes new bottom is greater than coordinate z
            vial.save()
            vial.load_vial()

            # If calibrating first vial, offer to recalculate all positions
            if vial_index == 0:
                if input(
                    "\nRecalculate all vial positions in this holder? (y/n): "
                ).lower() in ["y", "yes", ""]:
                    base_y = goto.y
                    for i, v in enumerate(vials):
                        if i == 0:
                            continue
                        v.vial_data.coordinates = Coordinates(
                            goto.x, base_y - (i * VIAL_SPACING), original_coords.z
                        ).to_dict()
                        v.save()
                        v.load_vial()
                    print(f"\nUpdated all {holder_type} vial positions")


def test_decapper(mill: Mill, *args, **kwargs):
    """
    Test the decapper by moving it to a vial and then moving it up and down
    """
    warn = input(
        "Warning: This test uses a hardcoded vial location and will control the mill if available to cap and decap the vial. Proceed? (y/n): "
    ).lower()
    if warn not in ["y", "yes"]:
        return
    decapper_test()


def rinse_electrode(mill: Mill, *args, **kwargs):
    """
    Rinse the electrode in the electrode bath
    """
    mill.rinse_electrode()


menu_options = {
    "0": check_mill_settings,
    "1": home_mill,
    "3": calibrate_wells,
    "4": calibrate_bottom_of_wellplate,
    "5": calibrate_echem_height,
    "6": calibrate_vial_holders,
    "7": calibrate_image_height,
    "8": test_decapper,
    "9": rinse_electrode,
    "q": quit_calibration,
}


def calibrate_mill(
    use_mock_mill: bool,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the mill to the wellplate and stock vials"""
    if use_mock_mill:
        mill = MockMill
    else:
        mill = Mill

    # Connect to the mill
    with mill() as cncmill:
        while True:
            print("\n\n")
            print("""\nWelcome to the mill calibration and positioning menu:""")
            for key, value in menu_options.items():
                print(f"{key}. {value.__name__.replace('_', ' ').title()}")
            option = input("Which operation would you like: ")
            if option == "q":
                break
            if option not in menu_options:
                print("Invalid option")
                continue
            else:
                menu_options[option](cncmill, wellplate, stock_vials, waste_vials)


def main():
    """Main function for testing the calibration functions"""
    testing = input("Enter 'y' to use testing configuration: ").lower() == "y"

    print("Testing mode:", testing)
    mode = input("Control the mill manually or automatically (manual/auto): ")

    if mode == "manual":
        print("Manual control of the mill")
        input("Open Candel and press enter to continue...")
        use_mock_mill = True

    elif mode == "auto":
        print("Automatic control of the mill")
        use_mock_mill = False

    wellplate_to_use = Wellplate()
    stock_vials_to_use: Sequence[StockVial] = read_vials()[0]
    waste_vials_to_use: Sequence[WasteVial] = read_vials()[1]

    calibrate_mill(
        use_mock_mill, wellplate_to_use, stock_vials_to_use, waste_vials_to_use
    )


if __name__ == "__main__":
    main()
