"""PEDOT Experiments Analyzer."""

# pylint: disable=line-too-long
from configparser import ConfigParser
from pathlib import Path

import pandas as pd
from panda_experiment_analyzers.example_analyzer import Analyzer as example_analysis
from panda_experiment_analyzers.pedot.sql_ml_functions import \
    insert_ml_training_data
from panda_lib import experiment_class, scheduler
from panda_lib.config.config_tools import read_testing_config
from panda_lib.correction_factors import correction_factor
from panda_lib.experiment_class import (ExperimentResultsRecord,
                                        insert_experiment_result,
                                        select_specific_result)
from panda_lib.slack_tools.SlackBot import SlackBot
from panda_lib.sql_tools.sql_system_state import get_current_pin

from . import PEDOT_FindLAB as lab
from . import PEDOT_MetricsCalc as met
from .ml_input import populate_required_information as analysis_input
from .ml_model import pedot_model
from .pedot_classes import (MLInput, MLOutput, MLTrainingData, PEDOTMetrics,
                            PEDOTParams, RawMetrics, RequiredData)


class Analyzer(example_analysis):
    """PEDOT Experiments Analyzer."""
    CURRENT_PIN = get_current_pin()

    PROJECT_ID = 16
    config = ConfigParser()
    config.read("panda_lib/config/panda_sdl_config.ini")

    # Set up the ML filepaths, for this project this is hardcoded only here
    ml_file_paths = MLInput(
        training_file_path=Path("ml_model/training_data/MLTrainingData_PEDOT.csv"),
        model_base_path=Path("ml_model/pedot_gp_model_v8"),
        counter_file_path=Path("ml_model/model_counter.txt"),
        BestTestPointsCSV=Path("ml_model/BestTestPoints.csv"),
        contourplots_path="ml_model/contourplots/contourplot",
    )

    def __init__(self):
        pass

    def main(self, experiment_id: int = None, generate_experiment: bool = True):
        """
        Main function for the PEDOT analyzer.

        If the system is in testing mode, the function will only generate a new experiment.
        It will not analyze the experiment.

        Args:
            experiment_id (int, optional): The experiment ID to analyze. Defaults to None.
            generate_experiment (bool, optional): Whether to generate a new experiment. Defaults to True.

        Returns:
            int: The ID of the new experiment if generate_experiment is True. Otherwise, None.

        """
        # Analyze the experiment
        self.analyze(experiment_id, add_to_training_data=True)

        if not generate_experiment:
            return None

        # Run the ML model
        new_experiment_id = self.run_ml_model()  # Generate a new experiment
        return new_experiment_id


    def run_ml_model(self, generate_experiment_id=None) -> MLOutput:
        """
        Runs the ML model for the PEDOT experiment.

        Args:
            generate_experiment_id ([type], optional): The experiment ID to generate. Defaults to None.
        """
        if generate_experiment_id is None:
            generate_experiment_id = scheduler.determine_next_experiment_id()

        # Run the ML model
        results = pedot_model(
            self.ml_file_paths.model_base_path,
            self.ml_file_paths.contourplots_path,
            experiment_id=generate_experiment_id,
        )

        ml_output = MLOutput(*results)

        params = PEDOTParams(
            dep_v=ml_output.v_dep,
            dep_t=ml_output.t_dep,
            concentration=ml_output.edot_concentration,
        )

        # Generate the next experiment
        exp_id = self.generator(
            params, experiment_name="PEDOT_Optimization", campaign_id=0
        )
        return exp_id





    def generator(
        self, params: PEDOTParams, experiment_name="PEDOT_Optimization", campaign_id=0
    ) -> int:
        """Generates a PEDOT experiment."""
        experiment_id = scheduler.determine_next_experiment_id()
        experiment = experiment_class.PEDOTExperiment(
            experiment_id=experiment_id,
            protocol_id=15,  # PEDOT protocol v4
            well_id="A1",  # Default to A1, let the program decide where else to put it
            well_type_number=4,
            experiment_name=experiment_name,
            pin=str(self.CURRENT_PIN),
            project_id=self.PROJECT_ID,
            project_campaign_id=campaign_id,
            solutions={"edot": 120, "liclo4": 0, "rinse": 120},
            solutions_corrected={},
            status=experiment_class.ExperimentStatus.NEW,
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
            ca_step_1_time=params.dep_t,
            ca_step_2_voltage=0.0,
            ca_step_2_time=0.0,
            ca_sample_rate=0.5,
            edot_concentration=params.concentration,
            analyzer=self.analyze,
            generator=self.run_ml_model,
        )

        # Add the correction factors
        for solution in experiment.solutions.keys():
            experiment.solutions_corrected[solution] = correction_factor(
                experiment.solutions[solution], experiment.well_type_number
            )

        scheduler.add_nonfile_experiments(
            [
                experiment,
            ]
        )
        return experiment_id


    def analyze(self, experiment_id: int, add_to_training_data:bool=False) -> MLTrainingData:
        """
        Analyzes the PEDOT experiment and returns the training data for the ML model.

        Args:
            experiment_id (int): The experiment ID to analyze.

        Returns:
            MLTrainingData: The training data to be used for the ML model.
        
        """
        if self.config.getboolean("OPTIONS", "testing"):
            return

        if experiment_id is None:
            experiment_id = scheduler.determine_next_experiment_id() - 1 # Get the last experiment ID

        input_data: RequiredData = analysis_input(experiment_id)
        metrics:RawMetrics = lab.rgbtolab(input_data)
        results = met.process_metrics(metrics, input_data)

        # insert the metrics as experiment results
        list_of_raw_metrics = [
            ExperimentResultsRecord(
                experiment_id=results.experiment_id,
                result_type=metric_name,
                result_value=getattr(metrics, metric_name),
                context="PEDOT Raw Metrics",
            )
            for metric_name in RawMetrics.__annotations__.keys()
        ]

        for metric in list_of_raw_metrics:
            insert_experiment_result(metric)
            print("Inserted metric: ", metric.result_type)

        list_of_pedot_metrics = [
            ExperimentResultsRecord(
                experiment_id=results.experiment_id,
                result_type=metric_name,
                result_value=getattr(results, metric_name),
                context="PEDOT Metrics",
            )
            for metric_name in PEDOTMetrics.__annotations__.keys()
        ]

        for result in list_of_pedot_metrics:
            insert_experiment_result(result)

        ml_training_data = MLTrainingData(
            experiment_id=results.experiment_id,
            ca_step_1_voltage=input_data.ca_step_1_voltage,
            ca_step_1_time=input_data.ca_step_1_time,
            edot_concentration=input_data.edot_concentration,
            deltaE00=metrics.delta_e00,
            BleachChargePassed=results.BleachChargePassed,
            DepositionEfficiency=results.DepositionEfficiency,
            ElectrochromicEfficiency=results.ElectrochromicEfficiency,
        )

        # Add the new training data to the training file
        df_new_training_data = pd.DataFrame(
            {
                "deltaE": [ml_training_data.deltaE00],
                "voltage": [ml_training_data.ca_step_1_voltage],
                "time": [ml_training_data.ca_step_1_time],
                "bleachCP": [ml_training_data.BleachChargePassed],
                "concentration": [ml_training_data.edot_concentration],
            }
        )
        # Add to the training data file
        # df_new_training_data.to_csv(
        #     ml_file_paths.training_file_path, mode="a", header=False, index=False
        # )
        if add_to_training_data:
            insert_ml_training_data(df_new_training_data)

        return ml_training_data


    def share_analysis_to_slack(
        self, experiment_id: int, next_exp_id: int = None, slack: SlackBot = None
    ):
        """
        Share the analysis results with the slack data channel

        Args:
            experiment_id (int): The experiment ID to analyze
            next_exp_id (int, optional): The next experiment ID. Defaults to None.
            slack (SlackBot, optional): The slack bot. Defaults to None.
        """
        # If the AL campaign length is set, run the ML analysis
        # We do the analysis on the experiment that just finished
        if read_testing_config():
            return
        if slack is None:
            slack = SlackBot()

        # First built the analysis message about the just completed experiment
        roi_path = None
        delta_e00 = None

        try:
            roi_path = Path(
                select_specific_result(experiment_id, "coloring_roi_path").result_value
            )
        except AttributeError:
            pass
        try:
            delta_e00 = select_specific_result(experiment_id, "delta_e00").result_value
        except AttributeError:
            pass

        if roi_path is not None:
            slack.send_slack_file(
                "data",
                roi_path,
                f"ROI for Experiment {experiment_id}:",
            )
        if delta_e00 is not None:
            slack.send_message(
                "data", f"Delta E for Experiment {experiment_id}: {delta_e00}"
            )

        # Then fetch the ML results and build the message
        # Our list of relevant results
        results_to_find = [
            "PEDOT_Deposition_Voltage",
            "PEDOT_Deposition_Time",
            "PEDOT_Concentration",
            "PEDOT_Predicted_Mean",
            "PEDOT_Predicted_Uncertainty",
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
            Deposition Time: {ml_results[1]}\n
            Concentration: {ml_results[2]}\n
            Predicted Mean: {ml_results[3]}\n
            Predicted StdDev: {ml_results[4]}\n
            """

            # fetch the contour plot
            contour_plot = Path(
                select_specific_result(next_exp_id, "PEDOT_Contour_Plots").result_value
            )

            slack.send_message("data", ml_results_msg)
            if contour_plot is not None:
                slack.send_slack_file(
                    "data",
                    contour_plot,
                    f"contour_plot_{next_exp_id}",
                )

        return
