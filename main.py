"""
The main menue of PANDA_SDL.

Useful for one-off tasks that don't require the full PANDA_SDL program to run.
Or starting the PANDA_SDL either with or without mock instruments.
"""

import os
import sys
import textwrap
import time
from multiprocessing import Process, Queue
from threading import Event, Thread
from typing import Tuple

from PIL import Image

import mill_calibration_and_positioning
from hardware.pipette import (
    insert_new_pipette,
    select_pipette_status,
)
from license_text import show_conditions, show_warrenty
from panda_lib import experiment_loop, imaging, print_panda
from panda_lib.config import print_config_values as print_config
from panda_lib.config import read_config, read_testing_config, write_testing_config
from panda_lib.experiment_analysis_loop import analysis_worker, load_analyzers
from panda_lib.experiment_class import ExperimentBase
from panda_lib.labware import vials, wellplate
from panda_lib.sql_tools import (
    remove_testing_experiments,
    sql_generator_utilities,
    sql_protocol_utilities,
    sql_queue,
    sql_system_state,
    sql_wellplate,
)
from panda_lib.utilities import SystemState, input_validation

os.environ["KMP_AFFINITY"] = "none"
exp_loop_prcss: Process = None
exp_loop_status = None
exp_loop_queue: Queue = Queue()
exp_cmd_queue: Queue = Queue()
analysis_prcss: Process = None
analysis_status = None
status_queue: Queue = Queue()
slackbot_thread: Thread = None
slackThread_running = Event()

experiment_choices = ["0", "1"]
analysis_choices = ["10"]
blocking_choices = ["0", "1", "6", "7", "8", "9", "t", "q"]


# def run_panda_sdl_with_ml():
#     """Runs PANDA_SDL and enables the ML analysis."""
#     length = int(input("Enter the campaign length: ").strip().lower())

#     exp_processes = Process(
#         target=experiment_loop.experiment_loop_worker,
#         kwargs={
#             "status_queue": status_queue,
#             "process_id": ProcessIDs.CONTROL_LOOP,
#             "campaign_length": length,
#         },
#     )
#     exp_processes.start()
#     return exp_processes


# def run_panda_sdl_without_ml():
#     """Runs PANDA_SDL."""
#     while True:
#         one_off = input("Is this a one-off run? (y/n): ").strip().lower()
#         if not one_off:
#             print("Invalid choice. Please try again.")
#             continue
#         elif one_off[0] == "y":
#             exp_ids = print_queue_info()
#             try:
#                 spec_id = int(input("Enter the experiment ID: ").strip().lower())

#             except EOFError:
#                 spec_id = input("Enter the experiment ID: ").strip().lower()
#             except ValueError:
#                 print("Invalid experiment ID. Please try again.")
#                 continue
#             if spec_id not in exp_ids:
#                 print("Invalid experiment ID. Please try again.")
#                 continue

#             exp_processes = Process(
#                 target=experiment_loop.experiment_loop_worker,
#                 kwargs={
#                     "one_off": True,
#                     "status_queue": status_queue,
#                     "process_id": ProcessIDs.CONTROL_LOOP,
#                     "specific_experiment_id": spec_id,
#                 },
#             )
#             break
#         elif one_off[0] == "n":
#             exp_processes = Process(
#                 target=experiment_loop.experiment_loop_worker,
#                 kwargs={
#                     "status_queue": status_queue,
#                     "process_id": ProcessIDs.CONTROL_LOOP,
#                 },
#             )
#             break
#         else:
#             print("Invalid choice. Please try again.")
#             continue

#     exp_processes.start()
#     return exp_processes


def run_sila_experiment_function():
    queue_list = print_queue_info()
    exp_id = int(
        input_validation(
            "Enter the experiment ID: ",
            int,
            None,
            False,
            "Invalid experiment ID",
            queue_list,
        )
    )
    if not exp_id:
        return

    exp_processes = Process(
        target=experiment_loop.sila_experiment_loop_worker,
        kwargs={
            "status_queue": status_queue,
            "command_queue": exp_cmd_queue,
            "process_id": ProcessIDs.CONTROL_LOOP,
            "specific_experiment_id": exp_id,
        },
    )
    exp_processes.start()
    return exp_processes


def run_queue():
    """Runs the queue."""
    queue = print_queue_info()

    exp_processes = Process(
        target=experiment_loop.sila_experiment_loop_worker,
        kwargs={
            "status_queue": status_queue,
            "command_queue": exp_cmd_queue,
            "process_id": ProcessIDs.CONTROL_LOOP,
            "specific_experiment_ids": queue,
        },
    )
    exp_processes.start()

    return exp_processes


def change_wellplate():
    """Changes the current wellplate."""
    new_plate_type = int(input("Enter the new wellplate type: ").strip().lower())
    new_plate_numb = int(input("Enter the new wellplate number: ").strip().lower())

    new_plate = wellplate.Wellplate(
        create_new=True, plate_id=new_plate_numb, type_id=new_plate_type
    )
    if new_plate:
        print(f"New wellplate loaded: {new_plate.plate_data.id}")
        new_plate.activate_plate()
        print(
            f"Location of A1: {new_plate.plate_data.a1_x}, {new_plate.plate_data.a1_y}"
        )
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
    c_plate = wellplate.Wellplate(type_id=plate_type, plate_id=well_num)

    print(
        f"""
        Wellplate {well_num} - Type: {plate_type}
        Available new wells: {avail_wells}
        Location of A1: x={c_plate.plate_data.a1_x}, y={c_plate.plate_data.a1_y}
        Bottom Z: {c_plate.plate_data.bottom}
        Top Z: {c_plate.plate_data.top}
        Orientation: {c_plate.plate_data.orientation}
        Echem height: {c_plate.plate_data.echem_height}
        Image height: {c_plate.plate_data.image_height}
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
    exp_cmd_queue.put(SystemState.STOP)
    sql_system_state.set_system_status(SystemState.SHUTDOWN, "stopping PANDA_SDL")


def pause_panda_sdl():
    """Pauses the PANDA_SDL loop."""
    exp_cmd_queue.put(SystemState.PAUSE)
    sql_system_state.set_system_status(SystemState.PAUSE, "stopping PANDA_SDL")


def resume_panda_sdl():
    """Resumes the PANDA_SDL loop."""
    exp_cmd_queue.put(SystemState.RESUME)
    sql_system_state.set_system_status(SystemState.RESUME, "stopping PANDA_SDL")


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
    insert_new_pipette(capacity=new_capacity)


def instrument_check():
    """Runs the instrument check."""
    sql_system_state.set_system_status(SystemState.BUSY, "running instrument check")
    intruments, all_found = experiment_loop.test_instrument_connections(False)
    if all_found:
        input("Press Enter to continue...")
    else:
        input("Press Enter to continue...")

    experiment_loop.disconnect_from_instruments(intruments)
    return


def test_pipette():
    """Runs the pipette test."""
    sql_system_state.set_system_status(SystemState.BUSY, "running pipette test")
    from testing_and_validation.pump_suction_check import main as pipette_test

    pipette_test()


def import_vial_data():
    """Imports vial data from a csv file."""
    sql_system_state.set_system_status(SystemState.BUSY, "importing vial data")
    vials.import_vial_csv_file()


def generate_vial_data_template():
    """Generates a vial data template."""
    vials.generate_template_vial_csv_file()
    input("Press Enter to continue...")


def slack_monitor_bot(testing, running_flag: Event):
    """Runs the slack monitor bot."""
    try:
        bot = experiment_loop.SlackBot(test=testing)
        bot.send_message("alert", "PANDA Bot is monitoring Slack")

        while running_flag.is_set():
            try:
                time.sleep(15)
                bot.check_slack_messages(channel="alert")
                time.sleep(1)
                bot.check_slack_messages(channel="data")
            except KeyboardInterrupt:
                break
            except Exception as e:
                status_queue.put((ProcessIDs.SLACKBOT, f"An error occurred: {e}"))
                time.sleep(60)
                continue
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    finally:
        bot.off_duty()


def run_control_loop(uchoice: callable) -> Process:
    """Runs the experiment in a separate process."""
    exp_process = Process(target=uchoice)
    exp_process.start()
    return exp_process


def start_analsyis_loop():
    """Starts the analysis loop."""
    sql_system_state.set_system_status(SystemState.BUSY, "starting analysis loop")
    process = Process(target=analysis_worker, args=(status_queue, ProcessIDs.ANALYSIS))
    process.start()
    return process


def stop_analysis_loop():
    """Stops the analysis loop."""
    if analysis_prcss:
        while (
            get_process_status(status_queue, ProcessIDs.ANALYSIS, analysis_status)
            != "idle"
        ):
            time.sleep(1)

        stop_process(analysis_prcss)


def stop_control_loop():
    """Stops the control loop."""
    if exp_loop_prcss:
        while (
            get_process_status(status_queue, ProcessIDs.CONTROL_LOOP, exp_loop_status)
            != "idle"
        ):
            time.sleep(1)

        stop_process(exp_loop_prcss)


def stop_process(process: Process):
    """Stops a process."""
    process.terminate()
    process.join()


def update_well_status():
    """Manually update the status of a well on the current wellpalte."""
    wellplate_id = wellplate.read_current_wellplate_info()[0]
    well_ids = sql_wellplate.select_well_ids(wellplate_id)
    well_id = input_validation(
        "Enter the well ID to update: ", str, None, False, "Invalid Well ID", well_ids
    )
    status = input_validation("Enter the status of the well: ", str)
    sql_wellplate.update_well_status(well_id, wellplate_id, status)


def list_analysis_script_ids():
    """List the analysis script IDs in the database."""
    analyzers = load_analyzers()
    print("Analysis Script IDs:")
    for analyzer in analyzers:
        print(analyzer.ANALYSIS_ID)

    input("Press Enter to continue...")


def main_menu(reduced: bool = False) -> Tuple[callable, str]:
    """Main menu for PANDA_SDL."""
    menu_options = {
        "0": run_sila_experiment_function,
        "1": run_queue,
        "1.1": stop_panda_sdl,
        "1.2": pause_panda_sdl,
        "1.3": resume_panda_sdl,
        "2": change_wellplate,
        "2.1": change_wellplate_location,
        "2.2": remove_wellplate_from_database,
        "2.3": print_wellplate_info,
        "2.5": remove_training_data,
        "2.6": clean_up_testing_experiments,
        "2.7": update_well_status,
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
        "12": list_analysis_script_ids,
        "t": toggle_testing_mode,
        "r": refresh,
        "w": show_warrenty,
        "c": show_conditions,
        "env": print_config,
        "q": exit_program,
    }

    missing_labware = check_essential_labware()

    if reduced:
        # Remove the blocking options
        for key in blocking_choices:
            menu_options.pop(key, None)

    if missing_labware:
        # Prevent experiments from being run and prevent generation of experiments
        for key in experiment_choices:
            menu_options.pop(key, None)
        additional_blocked = ["4.1", "3.0", "3.1", "3.2", "3.3", "1.1", "1.2", "1.3"]
        for key in additional_blocked:
            menu_options.pop(key, None)

        print(f"""Missing essential labware:
{", ".join(missing_labware)}
Experiments and generation are disabled until the labware is present.""")

    while True:
        menu_items = list(menu_options.items())
        half = len(menu_items) // 2 + len(menu_items) % 2

        for i in range(half):
            left = f"{menu_items[i][0]}. {menu_items[i][1].__name__.replace('_', ' ').title()}"
            right = (
                f"{menu_items[i + half][0]}. {menu_items[i + half][1].__name__.replace('_', ' ').title()}"
                if i + half < len(menu_items)
                else ""
            )
            print(f"{left:<40} {right}")
        user_choice = input("Enter the number of your choice: ").strip().lower()

        if user_choice in menu_options:
            return menu_options[user_choice], user_choice
        input("Invalid choice. Please try again.")
        refresh()


def get_process_status(process_status_queue: Queue, process_id, current_status=None):
    """Get the latest status of a process from the status queue."""
    temp_queue = []
    latest_status = None
    while not process_status_queue.empty():
        pid, status = process_status_queue.get()
        # If the process ids match, and the status is different than the current
        # status save the status.
        # If the status is None use the current status
        if pid == process_id:
            if current_status is None or status != current_status:
                latest_status = status
            else:
                latest_status = current_status
        else:
            # Save the other process statuses back to the queue
            temp_queue.append((pid, status))

    for item in temp_queue:
        # Return to queue if not the process we are looking for
        process_status_queue.put(item)

    if latest_status is None:
        return current_status
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


def user_sign_in() -> str:
    """Signs the user in."""
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

    return user_name.strip().capitalize()


def start_slack_bot(event_flag: Event) -> Thread:
    """Starts the slack bot."""
    slack_thread = Thread(
        target=slack_monitor_bot, args=(read_testing_config(), event_flag)
    )
    slack_thread.start()
    return slack_thread


def get_active_db():
    """Get the active database according to the config file."""
    if read_testing_config():
        return read_config()["TESTING"]["testing_db_address"]
    else:
        return read_config()["PRODUCTION"]["production_db_address"]


def check_essential_labware():
    """Check if the essential labware is present."""
    missing = []

    # Check if the stock and waste vials are present
    stock_vials, waste_vials = vials.read_vials()
    if not stock_vials:
        missing.append("stock vials")

    if not waste_vials:
        missing.append("waste vials")

    # Check if the wellplate is present
    wellplate_id, _, new_wells = wellplate.read_current_wellplate_info()
    if not wellplate_id:
        missing.append("wellplate")

    if new_wells is None or new_wells == 0:
        missing.append("new wells")

    # Check if the pipette is present
    current_pipette = select_pipette_status()
    if not current_pipette:
        missing.append("pipette")

    return missing


if __name__ == "__main__":
    config = read_config()
    slackThread_running.set()
    discalimer()
    time.sleep(2)
    sql_protocol_utilities.read_in_protocols()
    banner()

    try:
        user_name = user_sign_in()
        slackbot_thread = start_slack_bot(slackThread_running)
        while True:
            os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
            num, p_type, new_wells = wellplate.read_current_wellplate_info()
            try:
                current_pipette = select_pipette_status()
            except AttributeError:
                insert_new_pipette()
                current_pipette = select_pipette_status()
            remaining_uses = int(round((2000 - current_pipette.uses) / 2, 0))
            exp_loop_status = get_process_status(
                status_queue, ProcessIDs.CONTROL_LOOP, exp_loop_status
            )
            analysis_status = get_process_status(
                status_queue, ProcessIDs.ANALYSIS, analysis_status
            )
            # slackbot_status = get_process_status(status_queue, ProcessIDs.SLACKBOT, slackbot_status)
            banner()
            print(
                f"""
Welcome {user_name}!
Testing mode is {"ENABLED" if read_testing_config() else "DISABLED"}
DB: {get_active_db()}

The current wellplate is #{num} - Type: {p_type} - Available new wells: {new_wells}
The current pipette id is {current_pipette.id} and has {remaining_uses} uses left.
The queue has {sql_queue.count_queue_length()} experiments.
Process Status:
    Experiment Loop: {exp_loop_prcss.is_alive() if exp_loop_prcss else False} - {exp_loop_status}
    Analysis Loop: {analysis_prcss.is_alive() if analysis_prcss else False} - {analysis_status}
    Slack Bot: {slackThread_running.is_set()}
"""
            )

            # Get the function name and the choice key, reducing the options
            # if the experiment loop is running.
            function_name, choice_key = main_menu(
                exp_loop_prcss.is_alive() if exp_loop_prcss else False,
            )

            try:
                if choice_key in experiment_choices:
                    exp_loop_prcss = function_name()
                    continue
                elif choice_key in analysis_choices:
                    analysis_prcss = function_name()
                    continue
                function_name()
            except experiment_loop.ShutDownCommand:
                # Confirm that the control loop has been stopped
                if exp_loop_prcss:
                    exp_loop_prcss.terminate()
                    exp_loop_prcss.join()
                # The PANDA_SDL loop has been stopped but we don't want to exit the program
            except experiment_loop.OCPFailure:
                slack = experiment_loop.SlackBot()
                if slack.echem_error_procedure():
                    function_name()
                else:
                    continue

            except Exception as e:
                print(f"An error occurred: {e}")
                raise e  # Exit the program if an unknown error occurs
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting PANDA_SDL.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # End of program tasks
        if exp_loop_prcss:
            exp_loop_prcss.terminate()
            exp_loop_prcss.join()
        if analysis_prcss:
            analysis_prcss.terminate()
            analysis_prcss.join()
        if slackbot_thread:
            slackThread_running.clear()
            slackbot_thread.join()
