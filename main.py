"""
The main menue of ePANDA.

Useful for one-off tasks that don't require the full ePANDA program to run.
Or starting the ePANDA either with or without mock instruments.
"""
import os
import sys

from epanda_lib import (camera_call_camera, controller, generator_utilities, mill_control,scheduler, vials,
                        wellplate, mill_calibration_and_positioning)
from epanda_lib.config.config import STOCK_STATUS, WASTE_STATUS
from epanda_lib.config.config_tools import (read_testing_config,
                                            write_testing_config)


def run_epanda():
    """Runs ePANDA."""
    controller.main()

def change_wellplate():
    """Changes the current wellplate."""
    wellplate.load_new_wellplate(ask = True)

def reset_vials_stock():
    """Resets the stock vials."""
    vials.reset_vials('stock')

def reset_vials_waste():
    """Resets the waste vials."""
    vials.reset_vials('waste')

def input_new_vial_values_stock():
    """Inputs new values for the stock vials."""
    vials.input_new_vial_values('stock')

def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""
    vials.input_new_vial_values('waste')

def change_wellplate_location():
    """Changes the location of the current wellplate."""
    wellplate.change_wellplate_location()

def run_experiment_generator():
    """Runs the edot voltage sweep experiment."""
    available_generators = generator_utilities.get_generators()
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the terminal
    if not available_generators:
        print("No generators available.")
        return
    print("Available generators:")
    for generator in available_generators:
        print(generator)

    generator_id = input("Enter the id of the generator you would like to run: ")
    generator_id = int(generator_id)
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

    mill_calibration_and_positioning.calibrate_mill(
        mill,
        wellplate.Wellplate(),
        vials.read_vials(STOCK_STATUS),
        vials.read_vials(WASTE_STATUS)
    )

def test_camera():
    """Runs the mill control in testing mode."""
    camera_call_camera.capture_new_image()

def exit_program():
    """Exits the program."""
    print("Exiting ePANDA. Goodbye!")
    sys.exit()

options = {
    # '0': run_epanda,
    '1': run_epanda,
    '2': change_wellplate,
    '3': reset_vials_stock,
    '4': reset_vials_waste,
    '5': input_new_vial_values_stock,
    '6': input_new_vial_values_waste,
    '7': change_wellplate_location,
    '8': run_experiment_generator,
    '9': toggle_testing_mode,
    '10': calibrate_mill,
    '11': test_camera,
    'q': exit_program
}

if __name__ == "__main__":

    while True:
        # os.system('cls' if os.name == 'nt' else 'clear')  # Clear the terminal
        print("\n" * 10)
        print("Welcome to ePANDA!")
        print("Testing mode is currently:", "ON" if read_testing_config() else "OFF")
        current_wellplate = wellplate.read_current_wellplate()
        print(f"The current wellplate is #{current_wellplate[0]} - Type: {current_wellplate[1]} - Available Wells: {current_wellplate[2]}")
        print(f"The queue has {scheduler.get_queue_length()} experiments.")
        print("What would you like to do?")
        for key, value in options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice in options:
            options[user_choice]()
        else:
            print("Invalid choice. Please try again.")
            continue
