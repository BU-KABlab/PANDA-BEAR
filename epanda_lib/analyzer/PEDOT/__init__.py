from pathlib import Path
from . import PEDOT_FindLAB as lab
from . import PEDOT_MetricsCalc as met
from ml_input import populate_required_information as analysis_input
import pandas as pd
from dataclasses import dataclass

# Path: epanda_lib/analyzer/__init__.py


def pedot_analyzer(experiment_id: int):
    """Analyzes the PEDOT experiment."""

    input_data: pd.DataFrame = analysis_input(experiment_id)
    metrics = lab.rgbtolab(input_data)
    results = met.process_metrics(input_data, metrics)
    from epanda_lib.sql_utilities import (
        insert_experiment_results,
        ExperimentResultsRecord,
    )

    insert_experiment_results(
        ExperimentResultsRecord(experiment_id, "delta_e", metrics.Delta_E00, "PEDOT")
    )


@dataclass
class MLInput:
    experiment_id: int
    ca_step_1_voltage: float
    ca_step_1_time: float
    edot_concentration: float
    CA_deposition: Path
    CV_characterization: Path
    CA_bleaching: Path
    BeforeDeposition: Path
    AfterBleaching: Path
    AfterColoring: Path


@dataclass
class RawMetrics:
    experiment_id: int
    L_c: float
    A_c: float
    B_c: float
    L_b: float
    A_b: float
    B_b: float
    Delta_E00: float
    R_c: float
    G_c: float
    B_c: float
    R_b: float
    G_b: float
    B_b: float


@dataclass
class PEDOTMetrics:
    experiment_id: int
    DepositionChargePassed: float
    BleachChargePassed: float
    Capacitance: float
    DepositionEfficiency: float
    ElectrochromicEfficiency: float
