"""PEDOT Experiments Analyzer."""
#pylint: disable=line-too-long
from pathlib import Path
import pandas as pd
from epanda_lib.sql_utilities import (ExperimentResultsRecord,
                                      insert_experiment_result)

from . import PEDOT_FindLAB as lab
from . import PEDOT_MetricsCalc as met
from .experiment_generator import pedot_generator, determine_next_experiment_id
from .ml_input import populate_required_information as analysis_input
from .pedot_classes import MLInput, MLOutput, PEDOTParams, RequiredData, PEDOTMetrics, MLTrainingData, RawMetrics
from .ml_model import pedot_model

# Set up the ML filepaths, for this project this is hardcoded only here
ml_file_paths = MLInput(
    training_file_path = Path("epanda_lib/analyzer/pedot/ml_model/training_data/MLTrainingData_PEDOT.csv"),
    model_base_path = Path("epanda_lib/analyzer/pedot/ml_model/pedot_gp_model_v8_0.pth"),
    counter_file_path = Path("epanda_lib/analyzer/pedot/ml_model/model_counter.txt"),
    BestTestPointsCSV = Path("epanda_lib/analyzer/pedot/ml_model/BestTestPoints.csv"),
    contourplots_path = Path("epanda_lib/analyzer/pedot/ml_model/contourplots"),
)

def pedot_analyzer(experiment_id: int) -> MLTrainingData:
    """Analyzes the PEDOT experiment."""

    input_data:RequiredData = analysis_input(experiment_id)
    metrics = lab.rgbtolab(input_data)
    results = met.process_metrics(input_data, metrics)

    # insert the metrics as experiment results
    list_of_raw_metrics = [
        ExperimentResultsRecord(
            experiment_id=results.experiment_id,
            result_type=metric_name,
            result_value=getattr(results, metric_name),
        )
        for metric_name in RawMetrics.__annotations__.keys()
    ]

    for metric in list_of_raw_metrics:
        insert_experiment_result(metric)

    list_of_pedot_metrics = [
        ExperimentResultsRecord(
            experiment_id=results.experiment_id,
            result_type=metric_name,
            result_value=getattr(results, metric_name),
        )
        for metric_name in PEDOTMetrics.__annotations__.keys()
    ]

    for metric in list_of_pedot_metrics:
        insert_experiment_result(metric)

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
    return ml_training_data


def main(experiment_id:int = None):
    """Main function for the PEDOT analyzer."""
    # Get the experiment ID
    if experiment_id is None:
        experiment_id = determine_next_experiment_id() - 1

    # Analyze the experiment
    ml_training_data = pedot_analyzer(experiment_id)

    # Add the new training data to the training file
    df_new_training_data = pd.DataFrame({
        'deltaE': [ml_training_data.deltaE00],
        'voltage': [ml_training_data.ca_step_1_voltage],
        'time': [ml_training_data.ca_step_1_time],
        'bleachCP': [ml_training_data.BleachChargePassed],
        'concentration': [ml_training_data.edot_concentration],
    }
    )
    df_new_training_data.to_csv(
        ml_file_paths.training_file_path,
        mode='a',
        header=False,
        index=False
    )

    # Run the ML model
    results = pedot_model(
        ml_file_paths.training_file_path,
        ml_file_paths.model_base_path,
        ml_file_paths.counter_file_path,
        ml_file_paths.BestTestPointsCSV,
        ml_file_paths.contourplots_path
    )

    ml_output = MLOutput(
        *results
    )

    params = PEDOTParams(
        dep_v=ml_output.v_dep,
        dep_t=ml_output.t_dep,
        concentration=ml_output.edot_concentration,
    )

    # Generate the next experiment
    pedot_generator(params, experiment_name="PEDOT_Optimization", campaign_id=0)
