from dataclasses import dataclass
from pathlib import Path

@dataclass
class RequiredData:
    """Input data for the PEDOT analysis and ML model"""
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
    """Input data for the PEDOT analysis"""
    experiment_id: int
    l_c: float
    a_c: float
    b_c: float
    l_b: float
    a_b: float
    b_b: float
    delta_e00: float
    r_c_o: float
    g_c_o: float
    b_c_o: float
    r_b_o: float
    g_b_o: float
    b_b_o: float

@dataclass
class PEDOTMetrics:
    """Output of PEDOT analysis"""
    experiment_id: int
    DepositionChargePassed: float
    BleachChargePassed: float
    Capacitance: float
    DepositionEfficiency: float
    ElectrochromicEfficiency: float

@dataclass
class MLInput:
    """Input data for the ML model"""
    experiment_id: int
    ca_step_1_voltage: float
    ca_step_1_time: float
    edot_concentration: float
    deltaE00: float
    BleachChargePassed: float
    DepositionEfficiency: float
    ElectrochromicEfficiency: float

@dataclass
class PEDOTParams:
    """Parameters for PEDOT experiments"""
    well_letter: str = None
    well_number: int = None
    dep_v: float
    dep_t: float
