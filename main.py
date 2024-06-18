"""
The main menue of ePANDA.

Useful for one-off tasks that don't require the full ePANDA program to run.
Or starting the ePANDA either with or without mock instruments.
"""

# pylint: disable=broad-exception-caught, protected-access
import decimal
import os
import sys
import time
from pathlib import Path

from PIL import Image

import panda_lib.analyzer.pedot as pedot_analysis
from panda_lib import (
    flir_camera,
    controller,
    experiment_class,
    mill_calibration_and_positioning,
    mill_control,
    print_panda,
    scheduler,
    utilities,
    vials,
    wellplate,
)
from panda_lib.analyzer.pedot.pedot_classes import MLOutput, PEDOTParams
from panda_lib.config.config_tools import read_testing_config, write_testing_config
from panda_lib.sql_tools import (
    sql_generator_utilities,
    sql_protocol_utilities,
    sql_queue,
    sql_system_state,
    remove_testing_experiments
)
from panda_lib.analyzer.pedot import sql_ml_functions
from panda_lib.analyzer.pedot import pedot_analyzer


decimal.getcontext().prec = 6

def run_epanda_with_ml():
    """Runs ePANDA."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "running ePANDA"
    )
    length = int(input("Enter the campaign length: ").strip().lower())
    controller.main(al_campaign_length=length)


def run_epanda_without_ml():
    """Runs ePANDA."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "running ePANDA"
    )
    one_off = input("Is this a one-off run? (y/n): ").strip().lower()
    if one_off[0] == "y":
        controller.main(one_off=True)
    else:
        controller.main()


def genererate_pedot_experiment():
    """Generates a PEDOT experiment."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "generating PEDOT experiment"
    )
    dep_v = float(input("Enter the deposition voltage: ").strip().lower())
    dep_t = float(input("Enter the deposition time: ").strip().lower())
    concentration = float(input("Enter the concentration: ").strip().lower())
    params = PEDOTParams(dep_v=dep_v, dep_t=dep_t, concentration=concentration)
    pedot_analysis.pedot_generator(params=params)


def change_wellplate():
    """Changes the current wellplate."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "changing wellplate"
    )
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
    """Prints a summary of the current wellplate."""


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
    vials.input_new_vial_values("stock")


def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "inputting new vial values"
    )
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
        print(generator)

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
    if read_testing_config():
        # print("Cannot calibrate the mill in testing mode.")
        # return
        mill = mill_control.MockMill
    else:
        mill = mill_control.Mill

    sql_system_state.set_system_status(
        utilities.SystemState.CALIBRATING, "calibrating the mill"
    )

    mill_calibration_and_positioning.calibrate_mill(
        mill,
        wellplate.Wellplate(),
        vials.read_vials()[0],
        vials.read_vials()[1],
    )


def test_camera():
    """Runs the mill control in testing mode."""
    flir_camera.capture_new_image()


def generate_experiment_from_existing_data():
    """Generates an experiment from existing data using the ML model."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "generating experiment"
    )
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
        experiment_class.select_specific_result(
            next_experiment, "PEDOT_Contour_Plots"
        ).result_value  # should only return one value
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
            experiment_class.select_specific_result(
                next_experiment, result_type
            ).result_value  # should only return one value
        )
    # Compose message
    ml_results_msg = f"""
    Model #: {output.model_id}\n
    Experiment {next_experiment} Parameters and Predictions:\n
    Deposition Voltage: {ml_results[0]}\n
    Deposition Time: {ml_results[1]}\n
    Concentration: {ml_results[2]}\n
    Predicted Mean: {ml_results[3]}\n
    Predicted StdDev: {ml_results[4]}\n
    """
    print(ml_results_msg)

    # img = mpimg.imread(contour_plot)
    # plt.imshow(img)
    img = Image.open(contour_plot)
    img.show()
    print(
        f"V_dep: {output.v_dep}, T_dep: {output.t_dep}, EDOT Concentration: {output.edot_concentration}"
    )
    keep_exp = (
        input("Would you like to add an experiment with these values? (y/n): ")
        .strip()
        .lower()
    )
    if keep_exp[0] == "y":
        pedot_analysis.pedot_generator(
            params_for_next_experiment,
            experiment_name="PEDOT_Optimization",
            campaign_id=0,
        )
    else:
        print("Experiment not added.")

        # Delete the contour plot files, and the model based on the model ID
        contour_plot.with_suffix(".png").unlink()
        contour_plot.with_suffix(".svg").unlink()
        model_name = (
            Path(pedot_analysis.ml_file_paths.model_base_path).name
            + f"_{output.model_id}"
        )
        model_path = Path(pedot_analysis.ml_file_paths.model_base_path)
        model_path = model_path.with_name(model_name).with_suffix(".pth")
        model_path.unlink()
        sql_ml_functions.delete_model(output.model_id)

        return

def analyze_pedot_experiment():
    """Analyzes a PEDOT experiment."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "analyzing PEDOT experiment"
    )
    experiment_id = int(
        input("Enter the experiment ID to analyze: ").strip().lower()
    )

    to_train = input("Train the model? (y/n): ").strip().lower()
    dont_train = True if to_train[0] == "n" else False
    results = pedot_analysis.pedot_analyzer(experiment_id, dont_train)
    print(results)

def clean_up_testing_experiments():
    """Cleans up the testing experiments."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "cleaning up testing experiments"
    )
    remove_testing_experiments.main()

def exit_program():
    """Exits the program."""
    sql_system_state.set_system_status(
        utilities.SystemState.OFF, "exiting ePANDA"
    )
    print("Exiting ePANDA. Goodbye!")
    sys.exit()


def refresh():
    """
    Refreshes the main menue. Re-read the current wellplate info, and queue."""


def stop_epanda():
    """Stops the ePANDA loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.SHUTDOWN, "stopping ePANDA"
    )


def pause_epanda():
    """Pauses the ePANDA loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.PAUSE, "stopping ePANDA"
    )


def resume_epanda():
    """Resumes the ePANDA loop."""
    sql_system_state.set_system_status(
        utilities.SystemState.RESUME, "stopping ePANDA"
    )


def remove_training_data():
    """Removes the training data associated with a given experiment_id from the database."""
    experiment_id = int(
        input("Enter the experiment ID to remove the training data for: ")
        .strip()
        .lower()
    )
    sql_ml_functions.delete_training_data(experiment_id)


menu_options = {
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
    "2.5": remove_training_data,
    "2.6": clean_up_testing_experiments,
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
    "13": genererate_pedot_experiment,
    "14": analyze_pedot_experiment,
    "r": refresh,
    "q": exit_program,
}

if __name__ == "__main__":

    sql_system_state.set_system_status(
        utilities.SystemState.ON, "at main menu"
    )
    time.sleep(1)
    sql_protocol_utilities.read_in_protocols()

    while True:
        sql_system_state.set_system_status(
            utilities.SystemState.IDLE, "at main menu"
        )
        # os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
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
            pass  # The epanda loop has been stopped but we don't want to exit the program

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
                contiue_choice = slack.check_latest_message(channel_id)[0].strip().lower()
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

    sql_system_state.set_system_status(
        utilities.SystemState.OFF, "exiting ePANDA"
    )
