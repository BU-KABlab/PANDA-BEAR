"""
The main menue of PANDA_SDL.

Useful for one-off tasks that don't require the full PANDA_SDL program to run.
Or starting the PANDA_SDL either with or without mock instruments.
"""

# pylint: disable=broad-exception-caught, protected-access
import multiprocessing
import os
import sys
import textwrap
import threading
import time
from typing import Tuple

from PIL import Image

from license_text import show_conditions, show_warrenty
from panda_experiment_analyzers import analysis_worker
from panda_lib import (
    controller,
    imaging,
    pipette,
    print_panda,
    utilities,
    vials,
    wellplate,
)
from panda_lib.config import print_config_values as print_config
from panda_lib.config import read_config, read_testing_config, write_testing_config
from panda_lib.experiment_class import ExperimentBase
from panda_lib.movement import mill_calibration_and_positioning
from panda_lib.sql_tools import (
    remove_testing_experiments,
    sql_generator_utilities,
    sql_protocol_utilities,
    sql_queue,
    sql_system_state,
    sql_wellplate,
)

os.environ["KMP_AFFINITY"] = "none"


def run_panda_sdl_with_ml():
    """Runs PANDA_SDL and enables the ML analysis."""
    length = int(input("Enter the campaign length: ").strip().lower())

    exp_processes = multiprocessing.Process(
        target=controller.experiment_loop_worker,
        kwargs={
            "status_queue": status_queue,
            "process_id": ProcessIDs.CONTROL_LOOP,
            "campaign_length": length,
        },
    )
    exp_processes.start()
    return exp_processes


def run_panda_sdl_without_ml():
    """Runs PANDA_SDL."""
    while True:
        one_off = input("Is this a one-off run? (y/n): ").strip().lower()
        if not one_off:
            print("Invalid choice. Please try again.")
            continue
        elif one_off[0] == "y":

            exp_ids = print_queue_info()
            try:
                spec_id = int(input("Enter the experiment ID: ").strip().lower())

            except EOFError:
                spec_id = input("Enter the experiment ID: ").strip().lower()
            except ValueError:
                print("Invalid experiment ID. Please try again.")
                continue
            if spec_id not in exp_ids:
                print("Invalid experiment ID. Please try again.")
                continue

            exp_processes = multiprocessing.Process(
                target=controller.experiment_loop_worker,
                kwargs={
                    "one_off": True,
                    "status_queue": status_queue,
                    "process_id": ProcessIDs.CONTROL_LOOP,
                    "specific_experiment_id": spec_id,
                },
            )
            break
        elif one_off[0] == "n":
            exp_processes = multiprocessing.Process(
                target=controller.experiment_loop_worker,
                kwargs={
                    "status_queue": status_queue,
                    "process_id": ProcessIDs.CONTROL_LOOP,
                },
            )
            break
        else:
            print("Invalid choice. Please try again.")
            continue

    exp_processes.start()
    return exp_processes


def change_wellplate():
    """Changes the current wellplate."""
    wellplate_id = wellplate.load_new_wellplate(ask=True)
    if wellplate_id:
        location = sql_wellplate.select_wellplate_location(wellplate_id)
        print(f"New wellplate loaded: {wellplate_id}")
        print(f"Location of A1: {location[0]}, {location[1]}")
        input("Press Enter to continue...")
    else:
        print("No wellplate loaded.")
        input("Press Enter to continue...")


def remove_wellplate_from_database():
    """Removes the current wellplate from the database."""
    if not read_testing_config():
        print("Cannot remove the wellplate from the database in non-testing mode.")
        return
    plate_to_remove = int(
        input("Enter the wellplate number to remove: ").strip().lower()
    )

    wellplate._remove_wellplate_from_db(plate_to_remove)


def remove_experiment_from_database():
    """Removes a user provided experiment from the database."""
    experiments_to_remove = (
        input("Enter the experiment number(s) to remove seperated by commas: ")
        .strip()
        .lower()
    )
    experiments_to_remove = experiments_to_remove.split(",")

    removed = []
    not_removed = {}

    for experiment in experiments_to_remove:
        try:
            experiment = int(experiment)
            result, note = wellplate._remove_experiment_from_db(experiment)
            if result:
                removed.append(experiment)
            else:
                not_removed[experiment] = note
        except ValueError:
            print(f"Invalid experiment number: {experiment}")
            not_removed[experiment] = "Invalid experiment number"
            continue
        except Exception as removal_e:
            print(f"An error occurred: {removal_e}")
            not_removed[experiment] = removal_e
            continue

    print(f"Experiments removed: {removed}")
    print("Experiments not removed:")
    for experiment, note in not_removed.items():
        print(f"{experiment}: {note}")
    input("Press Enter to continue...")


def print_wellplate_info():
    """
    Prints a summary of the current wellplate.

    Wellplate ID - type
    Available new wells: x
    Location of A1: x, y

    """
    well_num, plate_type, avail_wells = wellplate.read_current_wellplate_info()
    (x, y, z_bottom, z_top, orientation, echem_height, image_height) = (
        sql_wellplate.select_wellplate_location(well_num)
    )
    print(
        f"""
        Wellplate {well_num} - Type: {plate_type}
        Available new wells: {avail_wells}
        Location of A1: x={x}, y={y}
        Bottom Z: {z_bottom}
        Top Z: {z_top}
        Orientation: {orientation}
        Echem height: {echem_height}
        Image height: {image_height}
        """
    )
    input("Press Enter to continue...")


def print_queue_info():
    """Prints a summary of the current queue."""
    current_queue = sql_queue.select_queue()
    print("Current Queue:")
    print("Experiment ID-Project ID-Campaign ID-Priority-Well ID")
    exp_ids = []
    for exp in current_queue:
        exp: ExperimentBase
        print(
            f"{exp.experiment_id}-{exp.project_id}-{exp.project_campaign_id}-{exp.priority}-{exp.well_id}"
        )
        exp_ids.append(exp.experiment_id)
    input("Press Enter to continue...")
    return exp_ids


def reset_vials_stock():
    """Resets the stock vials."""

    vials.reset_vials("stock")


def reset_vials_waste():
    """Resets the waste vials."""

    vials.reset_vials("waste")


def input_new_vial_values_stock():
    """Inputs new values for the stock vials."""

    print("\nNOTE: Vial names of none indicate a vial that doesn't exist.")
    vials.input_new_vial_values("stock")


def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""

    print("\nNOTE: Vial names of none indicate a vial that doesn't exist.")
    vials.input_new_vial_values("waste")


def change_wellplate_location():
    """Changes the location of the current wellplate."""

    wellplate.change_wellplate_location()


def run_experiment_generator():
    """Runs the edot voltage sweep experiment."""

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

    input("Press Enter to continue...")


def toggle_testing_mode():
    """Sets the testing mode."""
    mode = read_testing_config()
    write_testing_config(not mode)
    print("To complete the switch, please restart the program.")
    sys.exit()


def calibrate_mill():
    """Calibrates the mill."""

    mill_calibration_and_positioning.calibrate_mill(
        read_testing_config(),
        wellplate.Wellplate(),
        vials.read_vials()[0],
        vials.read_vials()[1],
    )


def test_image():
    """Runs the mill control in testing mode."""
    image = imaging.capture_new_image()
    open_image = Image.open(image)
    open_image.show()


def clean_up_testing_experiments():
    """Cleans up the testing experiments."""

    remove_testing_experiments.main()


def exit_program():
    """Exits the program."""

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
    while True:
        try:
            new_capacity = float(
                input("Enter the new capacity of the pipette tip (ul): ")
            )
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


def import_vial_data():
    """Imports vial data from a csv file."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "importing vial data"
    )
    vials.import_vial_csv_file()


def generate_vial_data_template():
    """Generates a vial data template."""
    vials.generate_template_vial_csv_file()
    input("Press Enter to continue...")


def slack_monitor_bot(testing, running_flag: threading.Event):
    """Runs the slack monitor bot."""
    try:
        bot = controller.SlackBot(test=testing)
        bot.send_message("alert", "PANDA Bot is monitoring Slack")

        while running_flag.is_set():
            try:
                time.sleep(10)
                bot.status = bot.check_slack_messages(channel="alert")
                bot.check_slack_messages(channel="data")
            except KeyboardInterrupt:
                break
            except Exception as e:
                status_queue.put((ProcessIDs.SLACKBOT, f"An error occurred: {e}"))
                time.sleep(15)
                continue
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    finally:
        bot.off_duty()


def run_control_loop(uchoice: callable) -> multiprocessing.Process:
    """Runs the experiment in a separate process."""
    exp_process = multiprocessing.Process(target=uchoice)
    exp_process.start()
    return exp_process


def start_analsyis_loop():
    """Starts the analysis loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "starting analysis loop"
    )
    process = multiprocessing.Process(
        target=analysis_worker, args=(status_queue, ProcessIDs.ANALYSIS)
    )
    process.start()
    return process


def stop_analysis_loop():
    """Stops the analysis loop."""
    if analysis_proceess:
        stop_process(analysis_proceess)


def stop_control_loop():
    """Stops the control loop."""
    if control_loop_process:
        stop_process(control_loop_process)


def stop_process(process: multiprocessing.Process):
    """Stops a process."""
    process.terminate()
    process.join()


experiment_choices = ["0", "1"]
analysis_choices = ["10"]
blocking_choices = ["0", "1", "6", "7", "8", "9", "t", "q"]


def main_menu(reduced: bool = False) -> Tuple[callable, str]:
    """Main menu for PANDA_SDL."""
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
        "3.4": import_vial_data,
        "3.5": generate_vial_data_template,
        "4": print_queue_info,
        "4.1": run_experiment_generator,
        "4.2": remove_experiment_from_database,
        "5": change_pipette_tip,
        "6": calibrate_mill,
        "7": test_image,
        "8": instrument_check,
        "9": test_pipette,
        "10": start_analsyis_loop,
        "11": stop_analysis_loop,
        "t": toggle_testing_mode,
        "r": refresh,
        "w": show_warrenty,
        "c": show_conditions,
        "env": print_config,
        "q": exit_program,
    }

    if reduced:
        # Remove the blocking options
        for key in blocking_choices:
            menu_options.pop(key, None)

    while True:
        print("\nWhat would you like to do?")
        for key, value in menu_options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice in menu_options:
            return menu_options[user_choice], user_choice
        input("Invalid choice. Please try again.")
        continue


def main_menu_options(reduced: bool = False) -> dict[str, callable]:
    """Main menu for PANDA_SDL."""
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
        "3.4": import_vial_data,
        "3.5": generate_vial_data_template,
        "4": print_queue_info,
        "4.1": run_experiment_generator,
        "4.2": remove_experiment_from_database,
        "5": change_pipette_tip,
        "6": calibrate_mill,
        "7": test_image,
        "8": instrument_check,
        "9": test_pipette,
        "10": start_analsyis_loop,
        "11": stop_analysis_loop,
        "t": toggle_testing_mode,
        "r": refresh,
        "w": show_warrenty,
        "c": show_conditions,
        "env": print_config,
        "q": exit_program,
    }

    if reduced:
        # Remove the blocking options
        for key in blocking_choices:
            menu_options.pop(key, None)

    return menu_options


def get_process_status(process_status_queue: multiprocessing.Queue, process_id):
    """Get the latest status of a process from the status queue."""
    latest_status = None
    temp_queue = []
    while not process_status_queue.empty():
        pid, status = process_status_queue.get()
        if pid == process_id:
            latest_status = status
        temp_queue.append((pid, status))

    for item in temp_queue:
        # Put the items back in the queue
        process_status_queue.put(item)

    return latest_status


class ProcessIDs:
    """Process IDs for the status queue."""

    CONTROL_LOOP = 0
    ANALYSIS = 1
    SLACKBOT = 2


def discalimer():
    """Prints the disclaimer."""
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


def banner():
    """Prints the banner."""
    print(f"\n{print_panda.print_panda()}\n")


if __name__ == "__main__":

    control_loop_process: multiprocessing.Process = None
    control_loop_status = None
    control_loop_queue: multiprocessing.Queue = multiprocessing.Queue()
    analysis_proceess: multiprocessing.Process = None
    analysis_status = None
    status_queue: multiprocessing.Queue = multiprocessing.Queue()
    slackThread_running = threading.Event()
    slackThread_running.set()

    config = read_config()

    discalimer()
    time.sleep(2)

    sql_protocol_utilities.read_in_protocols()

    banner()
    # User sign in
    try:
        while True:
            user_name = input("Enter your username: ").strip().lower()
            # Look up user in db

            # If user is not found, ask if they would like to create a new user

            # If user is found, ask for password

            # If password is correct, continue to main menu

            # If password is incorrect, ask if they would like to try again

            # If user chooses to try again, repeat password input

            # If user chooses to exit, exit the program
            break

        slackbot_thread = threading.Thread(
            target=slack_monitor_bot,
            args=(read_testing_config(), slackThread_running),
            daemon=True,
        )
        slackbot_thread.start()
        # Main loop
        while True:

            os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
            banner()
            print(f"Welcome {user_name}!")
            print(
                "Testing mode is ", "ENABLED" if read_testing_config() else "DISABLED"
            )
            if read_testing_config():
                print("DB: ", read_config()["TESTING"]["testing_db_address"])
            else:
                print("DB: ", read_config()["PRODUCTION"]["production_db_address"])
            num, p_type, new_wells = wellplate.read_current_wellplate_info()
            current_pipette = pipette.select_pipette_status()

            new_control_loop_status = get_process_status(
                status_queue, ProcessIDs.CONTROL_LOOP
            )
            new_analysis_status = get_process_status(status_queue, ProcessIDs.ANALYSIS)
            # slackbot_status = get_process_status(status_queue, ProcessIDs.SLACKBOT)

            if (
                control_loop_status != new_control_loop_status
                and new_control_loop_status is not None
            ):
                control_loop_status = new_control_loop_status
            if (
                analysis_status != new_analysis_status
                and new_analysis_status is not None
            ):
                analysis_status = new_analysis_status

            print(
                f"""
The current wellplate is #{num} - Type: {p_type} - Available new wells: {new_wells}
The current pipette id is {current_pipette.id} and has {int(round((2000-current_pipette.uses)/2,0))} uses left.
The queue has {sql_queue.count_queue_length()} experiments.
Process Status:
    Control Loop: {control_loop_process.is_alive() if control_loop_process else False} - {control_loop_status}
    Analysis Loop: {analysis_proceess.is_alive() if analysis_proceess else False} - {analysis_status}
        """
            )
            function_name, choice_key = main_menu(
                control_loop_process.is_alive() if control_loop_process else False
            )

            try:
                if choice_key in experiment_choices:
                    control_loop_process = function_name()
                    continue
                elif choice_key in analysis_choices:
                    analysis_proceess = function_name()
                    continue
                function_name()
            except controller.ShutDownCommand:
                # Confirm that the control loop has been stopped
                if control_loop_process:
                    control_loop_process.terminate()
                    control_loop_process.join()
                # The PANDA_SDL loop has been stopped but we don't want to exit the program
            except controller.OCPFailure:
                slack = controller.SlackBot()
                if slack.echem_error_procedure():
                    function_name()
                else:
                    continue

            except Exception as e:
                print(f"An error occurred: {e}")
                raise e  # Exit the program if an unknown error occurs
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # End of program tasks
        if control_loop_process:
            control_loop_process.terminate()
            control_loop_process.join()
        if analysis_proceess:
            analysis_proceess.terminate()
            analysis_proceess.join()
        slackThread_running.clear()
        slackbot_thread.join()
