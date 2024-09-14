"""
The main menue of PANDA_SDL.

Useful for one-off tasks that don't require the full PANDA_SDL program to run.
Or starting the PANDA_SDL either with or without mock instruments.
"""

# pylint: disable=broad-exception-caught, protected-access
import sys
import textwrap
import time

from PIL import Image

from panda_lib.config.config_print import print_config_values as print_config
from panda_lib.config.config_print import resolve_config_paths
from panda_lib.config.config_tools import read_testing_config, write_testing_config, read_config

resolve_config_paths()  # Yes I know the import order is wrong, but this must be run before anything else is loaded
from main_menu_custom_fucntions import (
    generate_pedot_experiment_from_existing_data,
    genererate_pedot_experiment,
    analyze_pedot_experiment,
)
from license_text import show_conditions, show_warrenty
from panda_lib import (
    controller,
    flir_camera,
    mill_calibration_and_positioning,
    pipette,
    print_panda,
    scheduler,
    utilities,
    vials,
    wellplate,
)
from panda_lib.sql_tools import (
    remove_testing_experiments,
    sql_generator_utilities,
    sql_protocol_utilities,
    sql_queue,
    sql_system_state,
    sql_wellplate,
)


def run_panda_sdl_with_ml():
    """Runs PANDA_SDL and enables the ML analysis."""
    sql_system_state.set_system_status(utilities.SystemState.BUSY, "running PANDA_SDL")
    length = int(input("Enter the campaign length: ").strip().lower())
    controller.main(al_campaign_length=length)


def run_panda_sdl_without_ml():
    """Runs PANDA_SDL."""
    sql_system_state.set_system_status(utilities.SystemState.BUSY, "running PANDA_SDL")
    while True:
        one_off = input("Is this a one-off run? (y/n): ").strip().lower()
        if not one_off:
            print("Invalid choice. Please try again.")
            continue
        elif one_off[0] == "y":
            controller.main(one_off=True)
            break
        elif one_off[0] == "n":
            controller.main()
            break
        else:
            print("Invalid choice. Please try again.")
            continue


def change_wellplate():
    """Changes the current wellplate."""
    sql_system_state.set_system_status(utilities.SystemState.BUSY, "changing wellplate")
    wellplate.load_new_wellplate(ask=True)


def remove_wellplate_from_database():
    """Removes the current wellplate from the database."""
    if not read_testing_config():
        print("Cannot remove the wellplate from the database in non-testing mode.")
        return
    plate_to_remove = int(
        input("Enter the wellplate number to remove: ").strip().lower()
    )
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY,
        "removing wellplate from database",
        read_testing_config(),
    )
    wellplate._remove_wellplate_from_db(plate_to_remove)


def remove_experiment_from_database():
    """Removes a user provided experiment from the database."""
    experiment_to_remove = int(
        input("Enter the experiment number to remove: ").strip().lower()
    )
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY,
        "removing experiment from database",
        read_testing_config(),
    )
    wellplate._remove_experiment_from_db(experiment_to_remove)


def print_wellplate_info():
    """
    Prints a summary of the current wellplate.
    
    Wellplate ID - type
    Available new wells: x
    Location of A1: x, y
    
    """
    # input("Feature coming soon...")
    well_num, plate_type, avail_wells = wellplate.read_current_wellplate_info()
    x, y, z_bottom, z_top, orientation, echem_height = sql_wellplate.select_wellplate_location(num)
    print(
        f"""
        Wellplate {well_num} - Type: {plate_type}
        Available new wells: {avail_wells}
        Location of A1: x={x}, y={y}
        Bottom Z: {z_bottom}
        Top Z: {z_top}
        Orientation: {orientation}
        Echem height: {echem_height}
        """
    )
    input("Press Enter to continue...")


def print_queue_info():
    """Prints a summary of the current queue."""
    current_queue = sql_queue.select_queue()
    print("Current Queue:")
    for experiment in current_queue:
        print(experiment)

    input("Press Enter to continue...")


def reset_vials_stock():
    """Resets the stock vials."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "resetting stock vials"
    )
    vials.reset_vials("stock")


def reset_vials_waste():
    """Resets the waste vials."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "resetting waste vials"
    )
    vials.reset_vials("waste")


def input_new_vial_values_stock():
    """Inputs new values for the stock vials."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "inputting new vial values"
    )
    print("\nNOTE: Vial names of none indicate a vial that doesn't exist.")
    vials.input_new_vial_values("stock")


def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "inputting new vial values"
    )
    print("\nNOTE: Vial names of none indicate a vial that doesn't exist.")
    vials.input_new_vial_values("waste")


def change_wellplate_location():
    """Changes the location of the current wellplate."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "changing wellplate location"
    )
    wellplate.change_wellplate_location()


def run_experiment_generator():
    """Runs the edot voltage sweep experiment."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "generating experiment files"
    )
    sql_generator_utilities.read_in_generators()
    available_generators = sql_generator_utilities.get_generators()
    # os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
    print()
    if not available_generators:
        print("No generators available.")
        return
    print("Available generators:")
    for generator in available_generators:
        print(generator.id, generator.name)

    generator_id = (
        input("Enter the id of the generator you would like to run or 'q' to go back: ")
        .strip()
        .lower()
    )
    if generator_id == "q":
        return
    generator_id = int(generator_id)
    sql_protocol_utilities.read_in_protocols()
    generator = sql_generator_utilities.get_generator_name(generator_id)
    sql_generator_utilities.run_generator(generator_id)


def toggle_testing_mode():
    """Sets the testing mode."""
    mode = read_testing_config()
    write_testing_config(not mode)
    print("To complete the switch, please restart the program.")
    sys.exit()


def calibrate_mill():
    """Calibrates the mill."""
    sql_system_state.set_system_status(
        utilities.SystemState.CALIBRATING, "calibrating the mill"
    )

    mill_calibration_and_positioning.calibrate_mill(
        read_testing_config(),
        wellplate.Wellplate(),
        vials.read_vials()[0],
        vials.read_vials()[1],
    )


def test_image():
    """Runs the mill control in testing mode."""
    image = flir_camera.capture_new_image()
    open_image = Image.open(image)
    open_image.show()


def clean_up_testing_experiments():
    """Cleans up the testing experiments."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "cleaning up testing experiments"
    )
    remove_testing_experiments.main()


def exit_program():
    """Exits the program."""
    sql_system_state.set_system_status(utilities.SystemState.OFF, "exiting PANDA_SDL")
    print("Exiting PANDA_SDL. Goodbye!")
    sys.exit()


def refresh():
    """
    Refreshes the main menue. Re-read the current wellplate info, and queue."""


def stop_panda_sdl():
    """Stops the PANDA_SDL loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.SHUTDOWN, "stopping PANDA_SDL"
    )


def pause_panda_sdl():
    """Pauses the PANDA_SDL loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.PAUSE, "stopping PANDA_SDL"
    )


def resume_panda_sdl():
    """Resumes the PANDA_SDL loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.RESUME, "stopping PANDA_SDL"
    )


def remove_training_data():
    """Removes the training data associated with a given experiment_id from the database."""
    from panda_experiment_analyzers.pedot import sql_ml_functions

    experiment_id = int(
        input("Enter the experiment ID to remove the training data for: ")
        .strip()
        .lower()
    )
    sql_ml_functions.delete_training_data(experiment_id)


def change_pipette_tip():
    """Changes the pipette tip."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "changing pipette tip"
    )
    while True:
        try:
            new_capacity = float(input("Enter the new capacity of the pipette tip (ul): "))
            break
        except ValueError:
            print("Invalid input. Please try again.")
    pipette.insert_new_pipette(capacity=new_capacity)

def instrument_check():
    """Runs the instrument check."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "running instrument check"
    )
    intruments, all_found = controller.test_instrument_connections(False)
    if all_found:
        input("Press Enter to continue...")
    else:
        input("Press Enter to continue...")

    controller.disconnect_from_instruments(intruments)
    return

def test_pipette():
    """Runs the pipette test."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "running pipette test"
    )
    from testing_and_validation.pump_suction_test import main as pipette_test
    pipette_test()


menu_options = {
    "0": run_panda_sdl_with_ml,
    "1": run_panda_sdl_without_ml,
    "1.1": stop_panda_sdl,
    "1.2": pause_panda_sdl,
    "1.3": resume_panda_sdl,
    "2": change_wellplate,
    "2.1": change_wellplate_location,
    "2.2": remove_wellplate_from_database,
    "2.3": print_wellplate_info,
    "2.5": remove_training_data,
    "2.6": clean_up_testing_experiments,
    "3": reset_vials_stock,
    "3.1": reset_vials_waste,
    "3.2": input_new_vial_values_stock,
    "3.3": input_new_vial_values_waste,
    "4": print_queue_info,
    "4.1": run_experiment_generator,
    "4.2": remove_experiment_from_database,
    "5": change_pipette_tip,
    "6": calibrate_mill,
    "7": test_image,
    "8": generate_pedot_experiment_from_existing_data,
    "8.1": genererate_pedot_experiment,
    "8.2": analyze_pedot_experiment,
    "9": instrument_check,
    "10": test_pipette,
    "t": toggle_testing_mode,
    "r": refresh,
    "w": show_warrenty,
    "c": show_conditions,
    "env": print_config,
    "q": exit_program,
}

if __name__ == "__main__":
    config = read_config()
    print(
        textwrap.dedent(
            """\n
        PANDA SDL version 1.0.0, Copyright (C) 2024 Gregory Robben, Harley Quinn
        PANDA SDL comes with ABSOLUTELY NO WARRANTY; choose `show_warrenty'
        for more details.

        This is free software, and you are welcome to redistribute it
        under certain conditions; choose `show_conditions' for details.
    """
        ).strip()
    )

    sql_system_state.set_system_status(utilities.SystemState.ON, "at main menu")
    time.sleep(1)
    sql_protocol_utilities.read_in_protocols()

    while True:
        sql_system_state.set_system_status(utilities.SystemState.IDLE, "at main menu")
        # os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
        print()
        print(print_panda.print_panda())
        print()
        print("Welcome to PANDA_SDL!")
        print("Testing mode is currently:", "ON" if read_testing_config() else "OFF")
        if read_testing_config():
            print("Database address: ", read_config()["TESTING"]["testing_db_address"])
        else:
            print("Database address: ", read_config()["PRODUCTION"]["production_db_address"])
        num, p_type, new_wells = wellplate.read_current_wellplate_info()
        current_pipette = pipette.select_current_pipette_id()
        print(
            f"""
The current wellplate is #{num} - Type: {p_type} - Available new wells: {new_wells}
The current pipette id is {current_pipette}
The queue has {scheduler.get_queue_length()} experiments.
"""
        )
        print("\nWhat would you like to do?")
        for key, value in menu_options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ").strip().lower()
        try:
            if user_choice in menu_options:
                menu_options[user_choice]()
            else:
                print("Invalid choice. Please try again.")
                continue
        except controller.ShutDownCommand:
            pass  # The PANDA_SDL loop has been stopped but we don't want to exit the program

        except controller.OCPFailure:
            slack = controller.SlackBot()
            slack.send_slack_message(
                "alert", "OCP Failure has occured. Please check the system."
            )
            channel_id = slack.channel_id("alert")
            slack.take_screenshot(channel_id, "webcam")
            slack.take_screenshot(channel_id, "vials")
            time.sleep(5)
            slack.send_slack_message("alert", "Would you like to continue? (y/n): ")
            while True:
                contiue_choice = (
                    slack.check_latest_message(channel_id)[0].strip().lower()
                )
                if contiue_choice == "y":
                    break
                if contiue_choice == "n":
                    break
            if contiue_choice == "n":
                continue
            if contiue_choice == "y":
                menu_options[user_choice]()

        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the program if an unknown error occurs

    sql_system_state.set_system_status(utilities.SystemState.OFF, "exiting PANDA_SDL")
