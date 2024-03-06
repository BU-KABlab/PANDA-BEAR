import json
from typing import Sequence
from mill_control import Mill, MockMill, StockVial, WasteVial, Wellplate
from utilities import Coordinates, Instruments


def check_mill_settings(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Fetch the settings list from the grbl controller and compare to the settings file.
    If there are differences, ask the user if they would like to change the settings.
    If so, ask for the settings to change and the new value.
    Update the settings file and send the new setting to the mill.
    Confirm the setting has been applied and save the settings file.
    Repeat until the user is satisfied.
    """

    while True:
        response = mill.execute_command("$$")  # Get settings
        print(response)

        ## Check settings
        # Load settings from config and compare to current settings
        settings: dict = mill.config["settings"]
        # List out settings and note any differences.
        for setting in settings:
            if settings[setting] != response[setting]:
                print(
                    f"Setting {setting:<4} | Current: {response[setting]:<5}, Config: {settings[setting]:<5}"
                )
            else:
                print(f"Setting {setting:<4} | Current: {response[setting]:<5}")

        # Ask if user wants to change settings
        change_settings = input("Would you like to change any settings? (y/n): ")
        if change_settings.lower() != "y":
            break

        while True:
            # Ask for settings to change
            setting_to_change = input("Enter the setting you would like to change: ")
            if setting_to_change not in settings:
                print("Setting not found")
                continue
            # Ask for the new value
            new_value = input(f"Enter the new value for {setting_to_change}: ")
            # Update loaded settings file
            settings[setting_to_change] = new_value

            change_settings = input(
                "Would you like to change any other settings? (y/n): "
            )
            if change_settings.lower() != "y":
                break

        # Send the new setting to the mill
        for setting in settings:
            mill.execute_command(f"{setting}={settings[setting]}")
        # Confirm setting has been applied
        response = mill.execute_command("$$")  # Get settings
        if response == settings:
            print("Settings have been applied")
            # Save the settings file
            with open(mill.config_file, "w", encoding="utf-8") as f:
                json.dump(mill.config, f)
            break
        else:
            print("Settings have not been applied")


def calibrate_wellplate(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the wellplate to the mill

    Args:
        wellplate (Wellplate): _description_
        mill (Mill): _description_
    """
    # Enter well choice loop
    while True:
        well_id = input("Enter the well ID to test (e.g., A1) or done to end: ").lower()
        if well_id == "done":
            break

        # Provide the current coordinates of the well
        original_coordinates = wellplate.get_coordinates(well_id)
        print(f"Current coordinates of {well_id}: {original_coordinates}")

        # Move the pipette to the top of the well
        mill.safe_move(
            original_coordinates["x"],
            original_coordinates["y"],
            wellplate.z_top,
            Instruments.PIPETTE,
        )

        # Enter confirmation loop
        while True:
            current_coorinates = Coordinates(
                original_coordinates["x"],
                original_coordinates["y"],
                z=wellplate.z_top,
            )
            confirm = input("Is the pipette in the correct position? (yes/no): ")
            if confirm.lower() == "yes":
                break
            print(f"Current coordinates of {well_id}: {current_coorinates}")
            new_coordinates = Coordinates(
                float(input(f"Enter the new x coordinate for {well_id}: ")),
                float(input(f"Enter the new y coordinate for {well_id}: ")),
                z=wellplate.z_top,
            )

            # Safe move to the new coordinates
            mill.safe_move(
                new_coordinates.x,
                new_coordinates.y,
                wellplate.z_top,
                Instruments.PIPETTE,
            )

        coord_diff = Coordinates(
            new_coordinates.x - original_coordinates["x"],
            new_coordinates.y - original_coordinates["y"],
            z=0,
        )

        # Save the new coordinates to the wellplate object for that well
        # wellplate.set_coordinates(well_id, new_coordinates)
        # For now we will not be setting individual well coordinates
        # Instead we will set the coordinates for the entire wellplate, specifically A1 and then recalculate the rest
        a1_coordinates = wellplate.get_coordinates("A1")
        a1_coordinates["x"] += coord_diff.x
        a1_coordinates["y"] += coord_diff.y

        wellplate.a1_x = a1_coordinates["x"]
        wellplate.a1_y = a1_coordinates["y"]
        wellplate.write_wellplate_location()
        wellplate.recalculate_well_locations()


def calibrate_z_bottom_of_wellplate(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
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
        well_id = input("Enter a well ID to check the z_bottom or 'done' to finish: ")
        if well_id == "done":
            break

        current_z_bottom = wellplate.z_bottom
        print(f"Current z_bottom of {well_id}: {current_z_bottom}")

        mill.safe_move(
            wellplate.get_coordinates(well_id, "x"),
            wellplate.get_coordinates(well_id, "y"),
            current_z_bottom,
            Instruments.PIPETTE,
        )

        while True:
            confirm = input("Is the pipette in the correct position? (yes/no): ")
            if confirm.lower() == "yes":
                break

            new_z_bottom = float(
                input(
                    f"Enter the new z_bottom for {well_id} (current: {current_z_bottom}): "
                )
            )

            mill.safe_move(
                wellplate.get_coordinates(well_id, "x"),
                wellplate.get_coordinates(well_id, "y"),
                new_z_bottom,
                Instruments.PIPETTE,
            )

        wellplate.z_bottom = new_z_bottom


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
    # If the user does not confirm, ask the user to input the new coordinates (display current coordinates)
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
    pass


def home_mill(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Home the mill"""
    mill.home()
    print("Mill has been homed")


options = {
    "0": check_mill_settings,
    "1": home_mill,
    "2": calibrate_wellplate,
    "3": calibrate_z_bottom_of_wellplate,
    "4": calibrate_vials,
}


def calibrate_mill(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the mill to the wellplate and stock vials"""
    # Connect to the mill
    with mill:
        while True:
            print(
                """"Welcome to the mill calibration and positioning menu:
Menu:
0. Check mill settings
1. Home mill
2. Calibrate wellplate
3. Calibrate z_bottom of wellplate
4. Calibrate vials
q Exit
              """
            )
            option = input("Which operation would you like: ")
            if option == "q":
                break
            options[option](mill, wellplate, stock_vials, waste_vials)


if __name__ == "__main__":
    # Load the configuration file
    from vials import read_vials, STOCK_STATUS, WASTE_STATUS
    from config.config import TESTING
    print("Testing mode:", TESTING)
    input("Press enter to continue")
    # Create the mill object
    mill_to_use = MockMill()

    # Create the wellplate object
    wellplate_to_use = Wellplate()

    # Create the stock vial objects
    stock_vials_to_use: Sequence[StockVial] = read_vials(STOCK_STATUS)
    waste_vials_to_use: Sequence[WasteVial] = read_vials(WASTE_STATUS)

    calibrate_mill(mill_to_use, wellplate_to_use, stock_vials_to_use, waste_vials_to_use)
