from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

@dataclass
class RequiredData:
    """Input data for the PAMA Contact Angle analysis and ML model"""
  
    experiment_id: int
    ca_step_1_voltage: float
    ca_step_1_time: float
    pama_concentration: float
    contact_angle_volume: float
    DuringContactAngle: Path #image path used for the contact angle analysis
    s_red_px: float
    s_blue_px: float

    # image_path: Path
    # image_name: str

@dataclass
class RawMetrics:
    """Input data for the PAMA Contact Angle RF model analysis"""

    experiment_id: int
    contact_angle_volume: float
    s_red_px: float
    s_blue_px: float

@dataclass
class PAMAMetrics:
    """Output of PAMA Contact Angle RF model analysis"""

    experiment_id: int
    Predicted_Contact_Angle_deg: float

@dataclass
class MLTrainingData:
    """Input data for the ML model"""

    experiment_id: int
    ca_step_1_voltage: float
    pama_concentration: float
    Predicted_Contact_Angle_deg: float

@dataclass
class MLInput:
    """The filepaths for the ML model's data and supporting files"""

    training_file_path: Path
    model_base_path: Path
    counter_file_path: Path
    BestTestPointsCSV: Path
    contourplots_path: Path


@dataclass
class MLOutput:
    """Output of the ML model"""

    v_dep: float
    pama_concentration: float
    predicted_mean: float
    predicted_stddev: float
    contour_plot: Path = None
    model_id: int = None


@dataclass
class PAMAParams:
    """Parameters for PAMA experiments"""

    dep_v: float
    well_letter: str = None
    well_number: int = None
    concentration: float = 0.1
