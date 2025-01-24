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
from typing import Sequence

from panda_lib.config.config_tools import read_config
from panda_lib.labware.vials import StockVial, Vial, WasteVial, read_vials
from panda_lib.labware.wellplate import Wellplate
from panda_lib.log_tools import setup_default_logger
from panda_lib.panda_gantry import Coordinates
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.utilities import Instruments, input_validation

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
                mill.fetch_saved_config()
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
            mill.save_config()

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
    working_volume = mill.config["working_volume"]
    print(f"Current working volume: {working_volume}")

    if input("Would you like to change the working volume? (y/n): ").lower() in [
        "y",
        "yes",
        "",
    ]:
        new_working_volume = {}
        for coordinate in ["x", "y", "z"]:
            new_coordinate = input(
                f"Enter the new {coordinate.upper()} coordinate for the working volume or enter for no change: "
            )
            if new_coordinate != "":
                try:
                    new_working_volume[coordinate] = float(new_coordinate)
                except ValueError:
                    print("Invalid input, please try again")
                    continue
            else:
                new_working_volume[coordinate] = working_volume[coordinate]

        mill.config["working_volume"] = new_working_volume
        mill.save_config()
        print(f"New working volume: {working_volume}")


def update_electrode_bath(mill: Mill, *args, **kwargs):
    """
    Update the location of the electrode bath using the vial object
    """

    electrode_bath_vial = Vial("e1")
    electrode_bath_coordinates = electrode_bath_vial.coordinates()
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

        electrode_bath_vial.vial_data.coordinates = new_coordinates
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
    coordinates_changed = False
    while True:
        well_id = (
            input(
                "Enter the well ID to test (e.g., A1) toggle to switch to between instruments or done to end: "
            )
            .upper()
            .strip()
        )
        if well_id == "DONE":
            break
        if well_id == "TOGGLE":
            instrument = "electrode" if instrument == "pipette" else "pipette"
            print(f"Instrument has been toggled to {instrument}")
            well_id = input("Enter the well ID to test (e.g., A1): ").lower()

        if well_id not in wellplate.wells:
            print("Invalid well ID")
            continue

        well = wellplate.wells[well_id]
        original_coordinates = well.coordinates
        print(f"Current coordinates of {well_id}: {original_coordinates}")
        current_coordinates = original_coordinates
        mill.safe_move(
            coordinates=well.top_coordinates,
            tool=instrument,
        )

        while True:
            confirm = input(f"Is the {instrument} in the correct position? (yes/no): ")
            if confirm.lower().strip()[0] in ["y", ""]:
                break
            print(f"Current coordinates of {well_id}: {current_coordinates}")
            coordinates_changed = True

            new_x = input_validation(
                f"Enter the new X coordinate for {well_id} or enter for no change: ",
                (int, float),
                (mill.working_volume.x, 0),
                allow_blank=1,
                default=original_coordinates["x"],
            )
            new_y = input_validation(
                f"Enter the new Y coordinate for {well_id} or enter for no change: ",
                (int, float),
                (mill.working_volume.y, 0),
                allow_blank=1,
                default=original_coordinates["y"],
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

            new_coordinates = Coordinates(new_x, new_y, wellplate.top)
            mill.safe_move(coordinates=new_coordinates, tool=instrument)

        if coordinates_changed:
            if input("Would you like to save the new coordinates? (y/n): ").lower() in [
                "y",
                "yes",
                "",
            ]:
                if well_id.upper() == "A1":
                    if input(
                        "Would you like to recalculate all well locations? (y/n): "
                    ).lower() in ["y", "yes", ""]:
                        wellplate.plate_data.a1_x = new_coordinates.x
                        wellplate.plate_data.a1_y = new_coordinates.y
                        wellplate.save()
                        wellplate.recalculate_well_positions()
                    else:
                        well.update_coordinates(new_coordinates)
                else:
                    well.update_coordinates(new_coordinates)


def calibrate_bottom_of_wellplate(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the bottom of the wellplate to the mill"""

    offset = mill.tool_manager.tool_offsets["pipette"].offset

    while True:
        well_id = (
            input("Enter a well ID to check the bottom of or 'done' to finish: ")
            .upper()
            .strip()
        )
        if well_id in ["DONE", "d"]:
            break

        well = wellplate.wells[well_id]
        print(f"Current bottom of {well_id}: {well.bottom}")
        print(f"Current coordinates of {well_id}: {wellplate.get_coordinates(well_id)}")
        input("Press enter to continue...")

        mill.safe_move(coordinates=well.top_coordinates, tool="pipette")
        goto = input_validation(
            "Enter a bottom to test or enter for no change: ", float, (-200, 0)
        )
        if not goto:
            goto = well.bottom

        current = mill.safe_move(
            coordinates=Coordinates(well.x, well.y, goto), tool="pipette"
        )

        while True:
            confirm = (
                input(
                    f"Is the pipette in the correct position {current.z - offset.z}? (yes/no): "
                )
                .lower()
                .strip()[0]
            )
            if confirm in ["y", ""]:
                break

            goto = input_validation(
                f"Enter the new bottom for {well_id} (currently at: {goto}): ",
                float,
                (-200, 0),
            )
            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, goto), tool="pipette"
            )

        base_thickness = abs(goto - well.z)
        print(f"Setting well base_thickness to: {base_thickness}")
        if input("Is this correct? (y/n): ").lower() in ["y", "yes", ""]:
            well.well_data.base_thickness = base_thickness
        else:
            if input(
                f"How about: {current.z - goto}? Is this correct? (y/n): "
            ).lower() in ["y", "yes", ""]:
                base_thickness = current.z - goto
                well.well_data.base_thickness = current.z - goto
            else:
                print("Skipping well")
                continue

        well.save()
        print(f"New z_bottom for {well_id}: {well.bottom}")

        if input(
            "Would you like to apply this to the entire wellplate? (y/n): "
        ).lower() in ["y", "yes", ""]:
            wellplate.plate_data.base_thickness = base_thickness
            wellplate.save()
            wellplate.recalculate_well_positions()


def calibrate_echem_height(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the height for the echem"""
    response = input(
        "Electrode will move to 0 above A1. Press enter to proceed or 'q' to quit: "
    )
    if response.lower() == "q":
        return

    well = wellplate.wells["A1"]
    offset = mill.tool_manager.tool_offsets["electrode"].offset
    mill.safe_move(coordinates=well.top_coordinates, tool="electrode")
    print(
        f"Current echem height is set to: {wellplate.plate_data.echem_height} off the well bottom"
    )

    if input("Would you like to set a new echem height? (y/n): ").lower() in [
        "y",
        "yes",
        "",
    ]:
        while True:
            new_echem_height = input_validation(
                "Enter the new echem height or enter for no change: ", float, (0, 10)
            )
            if new_echem_height is None:
                new_echem_height = wellplate.echem_height
            current = mill.safe_move(
                coordinates=Coordinates(well.x, well.y, new_echem_height),
                tool=Instruments.ELECTRODE,
            )

            if input(
                f"Is the electrode in the correct position at {current.z - offset.z} ({new_echem_height} from the bottom)? (yes/no): "
            ).lower() in ["y", "yes", ""]:
                break

        if new_echem_height is not None:
            wellplate.plate_data.echem_height = new_echem_height
            wellplate.save()
            print(f"New echem height: {wellplate.echem_height}")


def calibrate_image_height(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """Calibrate the height for the image"""
    response = input("Lens will move above A1. Press enter to proceed or 'q' to quit: ")
    if response.lower() == "q":
        return

    well = wellplate.wells["A1"]

    mill.safe_move(
        coordinates=Coordinates(well.x, well.y, wellplate.plate_data.image_height),
        tool="lens",
    )
    print(f"Current image height is set to: {wellplate.plate_data.image_height}")

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

            if input(
                f"Is the image in the correct position at {current.z}? (yes/no): "
            ).lower() in ["y", "yes", ""]:
                break

        if new_image_height is not None:
            wellplate.plate_data.image_height = new_image_height
            wellplate.save()
            print(f"New image height: {wellplate.plate_data.image_height}")


def capture_well_photo_manually(mill: Mill, wellplate: Wellplate, *args, **kwargs):
    """
    Capture a photo of a well manually

    Asks the user to input the well ID to capture a photo of.
    Also asks for relevant experiment id, project id, campaign id, and context.
    Experiment id is an integer: 1000000 <= experiment_id <= 9999999
    Project id and campaign id are integers.
    Context is one of these strings: 'BeforeDeposition', 'AfterBleaching', 'AfterColoring'
    """
    pass  # TODO: Implement this function
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


menu_options = {
    "0": check_mill_settings,
    "1": home_mill,
    "3": calibrate_wells,
    "4": calibrate_bottom_of_wellplate,
    "5": calibrate_echem_height,
    # "6": calibrate_camera_focus,
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
            menu_options[option](cncmill, wellplate, stock_vials, waste_vials)


def main():
    """Main function for testing the calibration functions"""
    testing = input("Enter 'y' to use testing configuration: ").lower() == "y"

    print("Testing mode:", testing)
    input("Press enter to continue")

    wellplate_to_use = Wellplate()
    stock_vials_to_use: Sequence[StockVial] = read_vials()[0]
    waste_vials_to_use: Sequence[WasteVial] = read_vials()[1]

    calibrate_mill(True, wellplate_to_use, stock_vials_to_use, waste_vials_to_use)


if __name__ == "__main__":
    main()
