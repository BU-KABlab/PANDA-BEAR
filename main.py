"""
The main menue of ePANDA.

Useful for one-off tasks that don't require the full ePANDA program to run.
Or starting the ePANDA either with or without mock instruments.
"""
# pylint: disable=broad-exception-caught, protected-access

import os
import sys
import time

from epanda_lib import (
    camera_call_camera,
    controller,
    generator_utilities,
    mill_calibration_and_positioning,
    mill_control,
    protocol_utilities,
    scheduler,
    vials,
    wellplate,
    print_panda
)
from epanda_lib.config.config import STOCK_STATUS, WASTE_STATUS
from epanda_lib.config.config_tools import read_testing_config, write_testing_config
from epanda_lib.sql_utilities import set_system_status
from epanda_lib.utilities import SystemState


def run_epanda():
    """Runs ePANDA."""
    set_system_status(SystemState.BUSY, "running ePANDA", read_testing_config())
    controller.main()


def change_wellplate():
    """Changes the current wellplate."""
    set_system_status(SystemState.BUSY, "changing wellplate", read_testing_config())
    wellplate.load_new_wellplate(ask=True)


def remove_wellplate_from_database():
    """Removes the current wellplate from the database."""
    if not read_testing_config():
        print("Cannot remove the wellplate from the database in non-testing mode.")
        return
    plate_to_remove = int(
        input("Enter the wellplate number to remove: ").strip().lower()
    )
    set_system_status(
        SystemState.BUSY, "removing wellplate from database", read_testing_config()
    )
    wellplate._remove_wellplate_from_db(plate_to_remove)


def reset_vials_stock():
    """Resets the stock vials."""
    set_system_status(SystemState.BUSY, "resetting stock vials", read_testing_config())
    vials.reset_vials("stock")


def reset_vials_waste():
    """Resets the waste vials."""
    set_system_status(SystemState.BUSY, "resetting waste vials", read_testing_config())
    vials.reset_vials("waste")


def input_new_vial_values_stock():
    """Inputs new values for the stock vials."""
    set_system_status(
        SystemState.BUSY, "inputting new vial values", read_testing_config()
    )
    vials.input_new_vial_values("stock")


def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""
    set_system_status(
        SystemState.BUSY, "inputting new vial values", read_testing_config()
    )
    vials.input_new_vial_values("waste")


def change_wellplate_location():
    """Changes the location of the current wellplate."""
    set_system_status(
        SystemState.BUSY, "changing wellplate location", read_testing_config()
    )
    wellplate.change_wellplate_location()


def run_experiment_generator():
    """Runs the edot voltage sweep experiment."""
    set_system_status(
        SystemState.BUSY, "generating experiment files", read_testing_config()
    )
    generator_utilities.read_in_generators()
    available_generators = generator_utilities.get_generators()
    # os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
    print()
    if not available_generators:
        print("No generators available.")
        return
    print("Available generators:")
    for generator in available_generators:
        print(generator)

    generator_id = (
        input("Enter the id of the generator you would like to run or 'q' to go back: ")
        .strip()
        .lower()
    )
    if generator_id == "q":
        return
    generator_id = int(generator_id)
    protocol_utilities.read_in_protocols()
    generator = generator_utilities.get_generator_name(generator_id)
    generator_utilities.run_generator(generator_id)


def toggle_testing_mode():
    """Sets the testing mode."""
    mode = read_testing_config()
    write_testing_config(not mode)
    print("To complete the switch, please restart the program.")
    sys.exit()


def calibrate_mill():
    """Calibrates the mill."""
    if read_testing_config():
        # print("Cannot calibrate the mill in testing mode.")
        # return
        mill = mill_control.MockMill
    else:
        mill = mill_control.Mill

    set_system_status(
        SystemState.CALIBRATING, "calibrating the mill", read_testing_config()
    )

    mill_calibration_and_positioning.calibrate_mill(
        mill,
        wellplate.Wellplate(),
        vials.read_vials(STOCK_STATUS),
        vials.read_vials(WASTE_STATUS),
    )


def test_camera():
    """Runs the mill control in testing mode."""
    camera_call_camera.capture_new_image()


def exit_program():
    """Exits the program."""
    set_system_status(SystemState.OFF, "exiting ePANDA", read_testing_config())
    print("Exiting ePANDA. Goodbye!")
    sys.exit()


def refresh():
    """
    Refreshes the main menue. Re-read the current wellplate info, and queue."""


options = {
    # '0': run_epanda,
    "1": run_epanda,
    "2": change_wellplate,
    "2.1": remove_wellplate_from_database,
    "3": reset_vials_stock,
    "4": reset_vials_waste,
    "5": input_new_vial_values_stock,
    "6": input_new_vial_values_waste,
    "7": change_wellplate_location,
    "8": run_experiment_generator,
    "9": toggle_testing_mode,
    "10": calibrate_mill,
    "11": test_camera,
    "r": refresh,
    "q": exit_program,
}

if __name__ == "__main__":

    set_system_status(SystemState.ON, "at main menu", read_testing_config())
    time.sleep(1)

    while True:
        set_system_status(SystemState.IDLE, "at main menu", read_testing_config())
        os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
        print()
        print(print_panda.print_panda())
        print()
        print("Welcome to ePANDA!")
        print("Testing mode is currently:", "ON" if read_testing_config() else "OFF")
        num, p_type, free_wells = wellplate.read_current_wellplate_info()
        print(
            f"The current wellplate is #{num} - Type: {p_type} - Available Wells: {free_wells}"
        )
        print(f"The queue has {scheduler.get_queue_length()} experiments.")
        print("What would you like to do?")
        for key, value in options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ").strip().lower()
        try:
            if user_choice in options:
                options[user_choice]()
            else:
                print("Invalid choice. Please try again.")
                continue
        except controller.ShutDownCommand:
            pass  # The epanda loop has been stopped but we don't want to exit the program
        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the program if an unknown error occurs

    set_system_status(SystemState.OFF, "exiting ePANDA", read_testing_config())
