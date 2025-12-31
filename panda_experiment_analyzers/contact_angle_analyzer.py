"""
Contact Angle Experiments Analyzer
Author: Harley Quinn
Date created: 2025.07.11

This analyzer uses LED distance and droplet volume to estimate the contact angle of water on a substrate
"""
# pylint: disable=line-too-long
from configparser import ConfigParser
from pathlib import Path

import pandas as pd

from panda_experiment_analyzers.contact_angle.contact_angle_led_detect import process_image
from panda_experiment_analyzers.contact_angle.contact_angle_predict_ca_regression_model import predict_batch as predict_contact_angle

from panda_experiment_analyzers.contact_angle.ml_input import (
    populate_required_information as analysis_input,
)
from panda_experiment_analyzers.contact_angle.contact_angle_ml_gpr_model import fit_gpr as contact_angle_model
from panda_experiment_analyzers.contact_angle.contact_angle_classes import (
    MLInput,
    MLOutput,
    MLTrainingData,
    PAMAMetrics,
    PAMAParams,
    RawMetrics,
    RequiredData,
)

from panda_experiment_analyzers.contact_angle.sql_ml_functions import insert_ml_training_data

from panda_lib import scheduler
from panda_lib.experiments import ExperimentStatus, experiment_types
from panda_lib.experiments.results import (
    ExperimentResultsRecord,
    insert_experiment_result,
    select_specific_result,
)

from panda_lib.slack_tools.slackbot_module import SlackBot
from panda_lib.sql_tools.queries.system import get_current_pin
from panda_shared.config.config_tools import read_testing_config

CURRENT_PIN = get_current_pin()
ANALYSIS_ID = 5  # Replace with actual contact angle analyzer ID
PROJECT_ID = 99  # Replace with actual project ID

config = ConfigParser()
config.read("panda_lib/config/panda_sdl_config.ini")
CA_PREDICT_MODEL_PATH = Path("ml_model/contact_angle_rf_model.pkl")

ml_file_paths = MLInput(
    training_file_path=Path("contact_angle/ml_model/training_data/MLTrainingData_PAMA.csv"),
    model_base_path=Path("contact_angle/ml_model/contact_angle_gp_model"),
    counter_file_path=Path("contact_angle/ml_model/model_counter.txt"),
    BestTestPointsCSV=Path("contact_angle/ml_model/BestTestPoints.csv"),
    contourplots_path="contact_angle/ml_model/contourplots/contourplot",
)

def main(experiment_id: int = None, generate_experiment: bool = True):
    """
    Main function for the Contact Angle analyzer.

    If the system is in testing mode, the function will only generate a new experiment.
    It will not analyze the experiment.

    Args:
        experiment_id (int, optional): The experiment ID to analyze. Defaults to None.
        generate_experiment (bool, optional): Whether to generate a new experiment. Defaults to True.

    Returns:
        int: The ID of the new experiment if generate_experiment is True. Otherwise, None.

    """
    # Analyze the experiment
    analyze_contact_angle(experiment_id, add_to_training_data=True)

    if not generate_experiment:
        return None

    # Run the ML model
    new_experiment_id = run_ml_model()  # Generate a new experiment
    return new_experiment_id
def run_ml_model(generate_experiment_id=None) -> MLOutput:
    """
    Runs the ML model for the PAMA contact angle experiment.

    Args:
        generate_experiment_id ([type], optional): The experiment ID to generate. Defaults to None.
    """
    if generate_experiment_id is None:
        generate_experiment_id = scheduler.determine_next_experiment_id()

    # Run the ML model
    results = contact_angle_model(
        ml_file_paths.model_base_path,
        ml_file_paths.contourplots_path,
        experiment_id=generate_experiment_id,
    )

    ml_output = MLOutput(*results)

    params = PAMAParams(
        dep_v=ml_output.v_dep,
        concentration=ml_output.pama_concentration,
    )

    # Generate the next experiment
    exp_id = generator(params, experiment_name="PAMA_ContactAngle", campaign_id=0) # TODO: update campaign_id
    return exp_id

def generator(
    params: PAMAParams, experiment_name="PAMA_ContactAngle", campaign_id=0
) -> int:
    """Generates a PAMA experiment."""
    experiment_id = scheduler.determine_next_experiment_id()
    experiment = experiment_types.EchemExperimentBase(
        experiment_id=experiment_id,
        protocol_name=15,  # TODO: Update this for the PAMA protocol
        well_id="A1",  # Default to A1, let the program decide where else to put it
        well_type_number=4, # TODO: Update this based on the new well plates.
        experiment_name=experiment_name,
        pin=str(CURRENT_PIN),
        project_id=PROJECT_ID,
        project_campaign_id=campaign_id,
        solutions={"pama": 120, "solvent": 0, "rinse": 120}, # TODO: update this based on solutions we will use
        status=ExperimentStatus.NEW,
        filename=experiment_name + " " + str(experiment_id),
        # Echem specific
        ocp=1,
        baseline=0,
        cv=0,
        ca=1,
        ca_sample_period=0.1,
        ca_prestep_voltage=0.0,
        ca_prestep_time_delay=0.0,
        ca_step_1_voltage=params.dep_v,
        ca_step_1_time=600,
        ca_step_2_voltage=0.0,
        ca_step_2_time=0.0,
        ca_sample_rate=0.5,
        pama_concentration=params.concentration,
        analyzer=analyze,
        generator=run_ml_model,
        analysis_id=ANALYSIS_ID,
    )

    scheduler.schedule_experiments(
        [
            experiment,
        ]
    )
    return experiment_id

def analyze(experiment_id: int, add_to_training_data: bool = False) -> MLTrainingData:
    """
    Estimate contact angle from a top down image and store results in the database.

    Args:
        experiment_id (int): Experiment ID.

    Returns:
        MLTrainingData: The training data to be used for the ML model.
    """
    if config.getboolean("OPTIONS", "testing"):
        return None

    if experiment_id is None:
        experiment_id = (
            scheduler.determine_next_experiment_id() - 1
        )  # Get the last experiment ID

    input_data: RequiredData = analysis_input(experiment_id)
    
    # TODO: Implement contact angle processing workflow
    # The following placeholder code was from PEDOT analyzer and needs to be updated:
    # - Process the image using process_image() from ContactAngle_LEDdetect
    # - Predict contact angle using predict_contact_angle() from ContactAngle_PredictCA_RegressionModel
    # For now, we create placeholder metrics and results
    metrics = RawMetrics(
        experiment_id=experiment_id,
        contact_angle_volume=input_data.contact_angle_volume,
        s_red_px=input_data.s_red_px,
        s_blue_px=input_data.s_blue_px,
    )
    results = PAMAMetrics(
        experiment_id=experiment_id,
        Predicted_Contact_Angle_deg=0.0,  # TODO: Calculate actual contact angle
    )

    # insert the metrics as experiment results
    list_of_raw_metrics = [
        ExperimentResultsRecord(
            experiment_id=results.experiment_id,
            result_type=metric_name,
            result_value=getattr(metrics, metric_name),
            context="PAMA Raw Metrics",
        )
        for metric_name in RawMetrics.__annotations__.keys()
    ]

    for metric in list_of_raw_metrics:
        insert_experiment_result(metric)
        print("Inserted metric: ", metric.result_type)

    list_of_pama_metrics = [
        ExperimentResultsRecord(
            experiment_id=results.experiment_id,
            result_type=metric_name,
            result_value=getattr(results, metric_name),
            context="PAMA Metrics",
        )
        for metric_name in PAMAMetrics.__annotations__.keys()
    ]

    for result in list_of_pama_metrics:
        insert_experiment_result(result)

    ml_training_data = MLTrainingData(
        experiment_id=results.experiment_id,
        ca_step_1_voltage=input_data.ca_step_1_voltage,
        pama_concentration=input_data.pama_concentration,
        Predicted_Contact_Angle_deg=results.Predicted_Contact_Angle_deg,
    )

    # Add the new training data to the training file
    df_new_training_data = pd.DataFrame(
        {
            "contact_angle": [ml_training_data.Predicted_Contact_Angle_deg],
            "voltage": [ml_training_data.ca_step_1_voltage],
            "concentration": [ml_training_data.pama_concentration],
        }
    )
    # Add to the training data file
    # df_new_training_data.to_csv(
    #     ml_file_paths.training_file_path, mode="a", header=False, index=False
    # )
    if add_to_training_data:
        insert_ml_training_data(df_new_training_data)

    return ml_training_data

def share_analysis_to_slack(experiment_id: int, next_exp_id: int = None, slack: SlackBot = None):
    """
    Share contact angle analysis results to Slack.

    Args:
        experiment_id (int): Experiment ID.
        next_exp_id (int, optional): The next experiment ID. Defaults to None.
        slack (SlackBot, optional): Slack bot instance.
    """
    if read_testing_config():
        return

    if slack is None:
        slack = SlackBot()

    centroid_path = None
    predicted_angle = None
    
    try:
        centroid_path = Path(
            select_specific_result(experiment_id, "centroid_path").result_value
        )
    except AttributeError:
        pass
      
    try:
        predicted_angle = select_specific_result(experiment_id, "ContactAngle_Predicted").result_value
    except AttributeError:
        pass

    if predicted_angle is not None:
        message = f"Experiment {experiment_id}: Predicted Contact Angle = {predicted_angle:.2f} degrees"
        slack.send_message("data", message)

    # Then fetch the ML results and build the message
    # Our list of relevant results
    results_to_find = [
        "PAMA_Deposition_Voltage",
        "PAMA_Concentration",
        "PAMA_Predicted_Mean",
        "PAMA_Predicted_Uncertainty",
    ]
    ml_results = []
    if (
        next_exp_id is not None
    ):  # If we have a next experiment ID, we can fetch the results
        for result_type in results_to_find:
            ml_results.append(
                select_specific_result(next_exp_id, result_type).result_value
            )
        # Compose message
        ml_results_msg = f"""
        Experiment {next_exp_id} Parameters and Predictions:\n
        Deposition Voltage: {ml_results[0]}\n
        Concentration: {ml_results[1]}\n
        Predicted Mean: {ml_results[2]}\n
        Predicted StdDev: {ml_results[3]}\n
        """

        # fetch the contour plot
        contour_plot = Path(
            select_specific_result(next_exp_id, "PAMA_Contour_Plots").result_value
        )

        slack.send_message("data", ml_results_msg)
        if contour_plot is not None:
            slack.send_slack_file(
                "data",
                contour_plot,
                f"contour_plot_{next_exp_id}",
            )

    return
