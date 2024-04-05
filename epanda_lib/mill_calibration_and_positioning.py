import json
from typing import Sequence
import os

from .mill_control import Mill, MockMill
from .utilities import Coordinates, Instruments
from .vials import StockVial, WasteVial
from .wellplate import WellCoordinates, Wellplate, Well


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
        #print(response)

        ## Check settings
        # Load settings from config and compare to current settings
        settings: dict = mill.config["settings"]
        # List out settings and note any differences.
        for setting in settings:
            if settings[setting] != int(response[setting]):
                print(
                    f"Setting {setting:<4} | Current: {response[setting]:<10}, Config: {settings[setting]:<5}"
                )
            else:
                print(f"Setting {setting:<4} | Current: {response[setting]:<10}")

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
            confirm = input("Is the pipette in the correct position? (yes/no): ").lower().strip()[0]
            if confirm.lower() == "y":
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


def calibrate_wells(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the locations of the individual wells in the wellplate"""
    # Enter well choice loop
    instrument = Instruments.PIPETTE
    while True:
        coordinates_changed = False
        well_id = input(
            "Enter the well ID to test (e.g., A1) toggle to switch to electrode or done to end: "
        ).lower()
        if well_id == "done":
            break

        if well_id == "toggle":
            instrument = (
                Instruments.ELECTRODE
                if instrument == Instruments.PIPETTE
                else Instruments.PIPETTE
            )
            print(f"Instrument has been toggled to {instrument}")
            well_id = input("Enter the well ID to test (e.g., A1): ").lower()

        # Provide the current coordinates of the well
        original_coordinates = wellplate.get_coordinates(well_id)
        print(f"Current coordinates of {well_id}: {original_coordinates}")

        # Move the pipette to the top of the well
        mill.safe_move(
            original_coordinates["x"],
            original_coordinates["y"],
            wellplate.z_top,
            instrument,
        )

        # Enter confirmation loop
        while True:
            current_coorinates = WellCoordinates(
                original_coordinates["x"],
                original_coordinates["y"],
                z_top=wellplate.z_top,
            )
            instrument: Instruments
            confirm = input(f"Is the {(instrument.value)}  in the correct position? (yes/no): ").lower().strip()[0]
            if confirm in ["y",""]:
                break
            print(f"Current coordinates of {well_id}: {current_coorinates}") #change to be the corrected coordinates if they have been changed
            coordinates_changed = True
            # gather new coordinates and test them for validity before trying to set them
            # enter validation loop
            while True:
                new_x = input(f"Enter the new x coordinate for {well_id} or enter for no change: ")
                new_y = input(f"Enter the new y coordinate for {well_id} or enter for no change: ")

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
                break # exit validation loop

            new_coordinates = WellCoordinates(
                new_x,
                new_y,
                z_top=wellplate.z_top,
            )

            # Safe move to the new coordinates
            mill.safe_move(
                new_coordinates.x,
                new_coordinates.y,
                wellplate.z_top,
                instrument,
            )

        if coordinates_changed:
            if well_id.upper() == "A1":
                recalc = input("Would you like to recalculate all well locations? (y/n): ")
                if recalc.lower() == "y":
                    wellplate.a1_x = new_coordinates.x
                    wellplate.a1_y = new_coordinates.y
                    wellplate.write_wellplate_location()
                    wellplate.recalculate_well_locations()
                    wellplate.write_well_status_to_file()
            else: # Update the well status file with the new well coordinates
                wellplate.set_coordinates(well_id, new_coordinates)
                #wellplate.write_well_status_to_file()
                wellplate.wells[well_id].save_to_db()


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
        well_id = input("Enter a well ID to check the z_bottom or 'done' to finish: ").upper().strip()
        if well_id == "DONE":
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
            confirm = input("Is the pipette in the correct position? (yes/no): ").lower().strip()[0]
            if confirm.lower() in ["y",""]:
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
        for well in wellplate.wells:
            well: Well
            well.depth = new_z_bottom
            # We do this instead of recalculating every well location incase
            # they are uniquely set
        wellplate.write_wellplate_location()
        wellplate.write_well_status_to_file() # but then we bulk save all wells to the db


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
    # "2": calibrate_wellplate,
    "3": calibrate_wells,
    "4": calibrate_z_bottom_of_wellplate,
    # "5": calibrate_vials,
    "q": 'quit',
}


def calibrate_mill(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Calibrate the mill to the wellplate and stock vials"""
    # Connect to the mill
    with mill() as mill:
        while True:
            os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
            print("""\nWelcome to the mill calibration and positioning menu:""")
            for key, value in options.items():
                print(f"{key}. {value.__name__.replace('_', ' ').title()}")
            option = input("Which operation would you like: ")
            if option == "q":
                mill.rest_electrode()
                break
            options[option](mill, wellplate, stock_vials, waste_vials)


if __name__ == "__main__":
    # Load the configuration file
    from .config.config import TESTING
    from .vials import STOCK_STATUS, WASTE_STATUS, read_vials

    print("Testing mode:", TESTING)
    input("Press enter to continue")
    # Create the mill object
    mill_to_use = MockMill()

    # Create the wellplate object
    wellplate_to_use = Wellplate()

    # Create the stock vial objects
    stock_vials_to_use: Sequence[StockVial] = read_vials(STOCK_STATUS)
    waste_vials_to_use: Sequence[WasteVial] = read_vials(WASTE_STATUS)

    calibrate_mill(
        mill_to_use, wellplate_to_use, stock_vials_to_use, waste_vials_to_use
    )
