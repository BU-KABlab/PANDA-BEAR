"""
The main menue of ePANDA.

Useful for one-off tasks that don't require the full ePANDA program to run.
Or starting the ePANDA either with or without mock instruments.
"""

# pylint: disable=broad-exception-caught, protected-access

import os
import sys
import time
from pathlib import Path

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
    print_panda,
)
from epanda_lib import sql_utilities
from epanda_lib.analyzer.pedot.pedot_classes import MLOutput, PEDOTParams
from epanda_lib.config.config import STOCK_STATUS, WASTE_STATUS
from epanda_lib.config.config_tools import read_testing_config, write_testing_config
from epanda_lib.sql_utilities import set_system_status, select_specific_result
from epanda_lib.utilities import SystemState
import epanda_lib.analyzer.pedot as pedot_analysis


def run_epanda_with_ml():
    """Runs ePANDA."""
    set_system_status(SystemState.BUSY, "running ePANDA", read_testing_config())
    controller.main(al_campaign_length=10)


def run_epanda_without_ml():
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


def remove_experiment_from_database():
    """Removes a user provided experiment from the database."""
    experiment_to_remove = int(
        input("Enter the experiment number to remove: ").strip().lower()
    )
    set_system_status(
        SystemState.BUSY, "removing experiment from database", read_testing_config()
    )
    wellplate._remove_experiment_from_db(experiment_to_remove)


def print_wellplate_info():
    """Prints a summary of the current wellplate."""


def print_queue_info():
    """Prints a summary of the current queue."""
    current_queue = sql_utilities.select_queue()
    print("Current Queue:")
    for experiment in current_queue:
        print(experiment)

    input("Press Enter to continue...")


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


def generate_experiment_from_existing_data():
    """Generates an experiment from existing data using the ML model."""
    set_system_status(SystemState.BUSY, "generating experiment", read_testing_config())
    next_experiment = scheduler.determine_next_experiment_id()
    output = pedot_analysis.pedot_model(
        pedot_analysis.ml_file_paths.training_file_path,
        pedot_analysis.ml_file_paths.model_base_path,
        pedot_analysis.ml_file_paths.counter_file_path,
        pedot_analysis.ml_file_paths.BestTestPointsCSV,
        pedot_analysis.ml_file_paths.contourplots_path,
        next_experiment,
    )
    output = MLOutput(*output)
    params_for_next_experiment = PEDOTParams(
        dep_v=output.v_dep,
        dep_t=output.t_dep,
        concentration=output.edot_concentration,
    )
    # The ML Model will then make a prediction for the next experiment
    # First fetch and send the contour plot
    contour_plot = Path(
        select_specific_result(next_experiment, "PEDOT_Contour_Plots").result_value
    )
    
    # Then fetch the ML results
    results_to_find = [
        "PEDOT_Deposition_Voltage",
        "PEDOT_Deposition_Time",
        "PEDOT_Concentration",
        "PEDOT_Predicted_Mean",
        "PEDOT_Predicted_Uncertainty",
    ]
    ml_results = []
    for result_type in results_to_find:
        ml_results.append(
            select_specific_result(next_experiment, result_type).result_value
        )
    # Compose message
    ml_results_msg = f"""
    Experiment {next_experiment} Parameters and Predictions:\n
    Deposition Voltage: {ml_results[0]}\n
    Deposition Time: {ml_results[1]}\n
    Concentration: {ml_results[2]}\n
    Predicted Mean: {ml_results[3]}\n
    Predicted StdDev: {ml_results[4]}\n
    """
    print(ml_results_msg)
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    img = mpimg.imread(contour_plot)
    plt.imshow(img)
    plt.show()

    print(
        f"V_dep: {output.v_dep}, T_dep: {output.t_dep}, EDOT Concentration: {output.edot_concentration}"
    )
    usr_choice = (
        input("Would you like to add an experiment with these values? (y/n): ")
        .strip()
        .lower()
    )
    if usr_choice[0] == "y":
        pedot_analysis.pedot_generator(
            params_for_next_experiment, experiment_name="PEDOT_Optimization", campaign_id=0
        )
    else:
        print("Experiment not added.")
        return


def exit_program():
    """Exits the program."""
    set_system_status(SystemState.OFF, "exiting ePANDA", read_testing_config())
    print("Exiting ePANDA. Goodbye!")
    sys.exit()


def refresh():
    """
    Refreshes the main menue. Re-read the current wellplate info, and queue."""


def stop_epanda():
    """Stops the ePANDA loop."""
    sql_utilities.set_system_status(
        SystemState.SHUTDOWN, "stopping ePANDA", read_testing_config()
    )


def pause_epanda():
    """Pauses the ePANDA loop."""
    sql_utilities.set_system_status(
        SystemState.PAUSE, "stopping ePANDA", read_testing_config()
    )


def resume_epanda():
    """Resumes the ePANDA loop."""
    sql_utilities.set_system_status(
        SystemState.RESUME, "stopping ePANDA", read_testing_config()
    )


options = {
    "0": run_epanda_with_ml,
    "1": run_epanda_without_ml,
    "1.1": stop_epanda,
    "1.2": pause_epanda,
    "1.3": resume_epanda,
    "2": change_wellplate,
    "2.1": remove_wellplate_from_database,
    "2.2": remove_experiment_from_database,
    "2.3": print_wellplate_info,
    "2.4": print_queue_info,
    "3": reset_vials_stock,
    "4": reset_vials_waste,
    "5": input_new_vial_values_stock,
    "6": input_new_vial_values_waste,
    "7": run_experiment_generator,
    "8": toggle_testing_mode,
    "9": calibrate_mill,
    "9.1": change_wellplate_location,
    "11": test_camera,
    "12": generate_experiment_from_existing_data,
    "r": refresh,
    "q": exit_program,
}

if __name__ == "__main__":

    set_system_status(SystemState.ON, "at main menu", read_testing_config())
    time.sleep(1)
    protocol_utilities.read_in_protocols()

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

        except controller.OCPFailure:
            slack = controller.SlackBot()
            slack.send_slack_message(
                "alert", "OCP Failure has occured. Please check the system."
            )
            channel_id = slack.channel_id("alert")
            slack._take_screenshot(channel_id, "webcam")
            slack._take_screenshot(channel_id, "vials")
            time.sleep(5)
            slack.send_slack_message("alert", "Would you like to continue? (y/n): ")
            while True:
                usr_choice = slack.check_latest_message(channel_id)[0].strip().lower()
                if usr_choice == "y":
                    break
                if usr_choice == "n":
                    break
            if usr_choice == "n":
                continue
            if usr_choice == "y":
                run_epanda_without_ml()

        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the program if an unknown error occurs

    set_system_status(SystemState.OFF, "exiting ePANDA", read_testing_config())
