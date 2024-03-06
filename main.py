"""
The main menue of ePANDA.

Useful for one-off tasks that don't require the full ePANDA program to run.
Or starting the ePANDA either with or without mock instruments.
"""
import os
import sys
from epanda_lib import controller, wellplate, vials
from epanda_lib.config.config_tools import read_testing_config, write_testing_config
TESTING = read_testing_config()

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

def edot_voltage_sweep_generator():
    """Runs the edot voltage sweep experiment."""
    from experiment_generators import exp_edot_voltage_sweep_generator
    exp_edot_voltage_sweep_generator.main()

def toggle_testing_mode():
    """Sets the testing mode."""
    write_testing_config(not TESTING)

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
    '8': edot_voltage_sweep_generator,
    '9': toggle_testing_mode,
    'q': exit_program
}

if __name__ == "__main__":
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear the terminal
        print("Welcome to ePANDA!")
        print("The current wellplate is", wellplate.save_current_wellplate()[0])
        print("TESTING MODE IS CURRENTLY", "ON" if read_testing_config() else "OFF")
        print("What would you like to do?")
        for key, value in options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ")
        if user_choice in options:
            options[user_choice]()
        else:
            print("Invalid choice. Please try again.")
            continue
