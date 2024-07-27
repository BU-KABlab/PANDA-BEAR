"""Reanalyze the given experiments for the correct rgb values"""

from panda_experiment_analyzers.pedot import PEDOT_FindLAB as lab
from panda_experiment_analyzers.pedot.ml_input import (
    populate_required_information as analysis_input
    )
from panda_experiment_analyzers.pedot.pedot_classes import RawMetrics, RequiredData
from panda_lib.experiment_class import (ExperimentResultsRecord,
                                      insert_experiment_results)

experiments = list(range(10000875, 10000896 + 1))
def recalculate_rgb(experiment_id: int):
    input_data: RequiredData = analysis_input(experiment_id)
    metrics: RawMetrics = lab.rgbtolab(input_data)
    results = []
    # we are only updating the RGB values so lets get them from metrics
    rco = metrics.r_c_o
    gco = metrics.g_c_o
    bco = metrics.b_c_o
    rbo = metrics.r_b_o
    gbo = metrics.g_b_o
    bbo = metrics.b_b_o
    # insert the metrics as experiment results
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="r_c_o", result_value=rco, context="reanalyzed RGB"
        )
    )
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="g_c_o", result_value=gco, context="reanalyzed RGB"
        )
    )
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="b_c_o", result_value=bco, context="reanalyzed RGB"
        )
    )
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="r_b_o", result_value=rbo, context="reanalyzed RGB"
        )
    )
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="g_b_o", result_value=gbo, context="reanalyzed RGB"
        )
    )
    results.append(
        ExperimentResultsRecord(
            experiment_id=experiment_id, result_type="b_b_o", result_value=bbo, context="reanalyzed RGB"
        )
    )

    insert_experiment_results(results)
    return results

for experiment_id in experiments:
    recalculate_rgb(experiment_id)
    print(f"Recalculated RGB values for experiment {experiment_id}")
