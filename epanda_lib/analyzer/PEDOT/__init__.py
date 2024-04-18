"""PEDOT Experiments Analyzer."""
from epanda_lib.sql_utilities import (ExperimentResultsRecord,
                                      insert_experiment_results)

from . import PEDOT_FindLAB as lab
from . import PEDOT_MetricsCalc as met
from .experiment_generator import pedot_generator
from .ml_input import populate_required_information as analysis_input
from .pedot_classes import MLInput, PEDOTMetrics, PlottingValues, RawMetrics


def pedot_analyzer(experiment_id: int) -> PlottingValues:
    """Analyzes the PEDOT experiment."""

    input_data:MLInput = analysis_input(experiment_id)
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
        insert_experiment_results(metric)

    list_of_pedot_metrics = [
        ExperimentResultsRecord(
            experiment_id=results.experiment_id,
            result_type=metric_name,
            result_value=getattr(results, metric_name),
        )
        for metric_name in PEDOTMetrics.__annotations__.keys()
    ]

    for metric in list_of_pedot_metrics:
        insert_experiment_results(metric)

    pv = PlottingValues(
        experiment_id=results.experiment_id,
        ca_step_1_voltage=input_data.ca_step_1_voltage,
        ca_step_1_time=input_data.ca_step_1_time,
        edot_concentration=input_data.edot_concentration,
        deltaE00=metrics.delta_e00,
        BleachChargePassed=results.BleachChargePassed,
        DepositionEfficiency=results.DepositionEfficiency,
        ElectrochromicEfficiency=results.ElectrochromicEfficiency,
    )
    return pv


def main():
    """Main function for the PEDOT analyzer."""
    experiment_id = 1
    plotting_values = pedot_analyzer(experiment_id)
    # ML model goes here and accepts plotting_values as input, then outputs the ML output
    pedot_generator(ml_output, experiment_name="PEDOT_Analysis", campaign_id=0)
