import hardpotato as hp
from panda_shared.config import read_data_dir
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
import pathlib
import logging
from decimal import Decimal
from typing import Tuple
import pandas as pd

global COMPLETE_FILE_NAME
logger = logging.getLogger("panda")


# =====================
# Parameter dataclasses
# =====================


@dataclass(config=ConfigDict(validate_assignment=True))
class OCPParameters:
    ttot: float = 1  # s, total time
    dt: float = 0.01  # s, time increment
    fileName: str = "OCP"  # base file name for data file
    header: str = "OCP"  # header for data file


@dataclass(config=ConfigDict(validate_assignment=True))
class CVParameters:
    Eini: float = -0.5  # V, initial potential
    Ev1: float = 0.5  # V, first vertex potential
    Ev2: float = -0.5  # V, second vertex potential
    Efin: float = -0.5  # V, final potential
    sr: float = 1  # V/s, scan rate
    dE: float = 0.001  # V, potential increment
    nSweeps: int = 2  # number of sweeps
    sens: float = 1e-6  # A/V, current sensitivity
    E2: float = 0.5  # V, potential of the second working electrode
    sens2: float = 1e-9  # A/V, current sensitivity of the second working electrode
    fileName: str = "CV"  # base file name for data file
    header: str = "CV"  # header for data file


@dataclass(config=ConfigDict(validate_assignment=True))
class CAParameters:
    Estep: float = 0.5  # V, step potential
    dt: float = 0.01  # s, time increment
    ttot: float = 1  # s, total time
    sens: float = 1e-6  # A/V, current sensitivity
    E2: float = 0.5  # V, potential of the second working electrode
    sens2: float = 1e-9  # A/V, current sensitivity of the second working electrode
    fileName: str = "CA"  # base file name for data file
    header: str = "CA"  # header for data file


@dataclass(config=ConfigDict(validate_assignment=True))
class MScriptParameters:
    script_path: str  # Path to the mscript file
    fileName: str = "MSCRIPT"  # base file name for data file
    header: str = "MSCRIPT"  # header for data file


def validate_file_name(file_name: str) -> str:
    """
    Check if the file name is missing a file extension.
    """
    if not file_name.endswith((".txt", ".csv")):
        file_name += ".txt"
    return file_name


# =====================
# Experiment functions
# =====================


def OCP(params: OCPParameters):
    """Run OCP experiment on EmStat Pico."""
    model = "emstatpico"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    ocp = hp.potentiostat.OCP(params.ttot, params.dt, COMPLETE_FILE_NAME, params.header)
    ocp.run()
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    data = hp.load_data.OCP(COMPLETE_FILE_NAME, folder, model)
    save_in_gamry_format(data, COMPLETE_FILE_NAME, params.header)


def cyclic(params: CVParameters):
    """Run CV experiment on EmStat Pico."""
    model = "emstatpico"
    folder = read_data_dir()
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    global COMPLETE_FILE_NAME
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    cv = hp.potentiostat.CV(
        params.Eini,
        params.Ev1,
        params.Ev2,
        params.Efin,
        params.sr,
        params.dE,
        params.nSweeps,
        params.sens,
        params.E2,
        params.sens2,
        COMPLETE_FILE_NAME,
        params.header,
    )
    cv.run()
    data = hp.load_data.CV(COMPLETE_FILE_NAME, folder, model)
    save_in_gamry_format(data, COMPLETE_FILE_NAME, params.header)


def chrono(params: CAParameters):
    """Run CA experiment on EmStat Pico."""
    model = "emstatpico"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    ca = hp.potentiostat.CA(
        params.Estep,
        params.dt,
        params.ttot,
        params.sens,
        params.E2,
        params.sens2,
        COMPLETE_FILE_NAME,
        params.header,
    )
    ca.run()
    data = hp.load_data.CA(COMPLETE_FILE_NAME, folder, model)
    save_in_gamry_format(data, COMPLETE_FILE_NAME, params.header)


def run_mscript(params: MScriptParameters):
    """Run custom mscript file on EmStat Pico."""
    model = "emstatpico"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    mscript = hp.potentiostat.MethodScript(
        None,
        None,
        params.script_path,
    )
    mscript.run()
    data = hp.load_data.MethodScript(COMPLETE_FILE_NAME, folder, model)
    save_in_gamry_format(data, COMPLETE_FILE_NAME, params.header)


# =====================
# Data saving utility
# =====================
def save_in_gamry_format(data, file_name: str, header: str):
    """
    Custom function for the panda_lib. Save data from Hardpotato in the Gamry format:
    ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    """
    gamry_data = {
        "Time": getattr(data, "t", None),  # Time in seconds
        "Vf": getattr(data, "E", None),  # Measured E vs. Eref
        "Vu": getattr(data, "U", None),  # Uncompensated voltage
        "Im": getattr(data, "I", None),  # Measured current
        "Vsig": getattr(data, "Vsig", None),  # Signal sent to Control Amp
        "Ach": getattr(data, "Ach", None),  # Measured Aux channel voltage
        "IERange": getattr(data, "IERange", None),  # Current range
        "Overload": getattr(data, "Overload", None),  # Overload status
        "StopTest": getattr(data, "StopTest", None),  # Stop flag
        "Cycle": getattr(data, "Cycle", None),  # Cycle number
        "Ach2": getattr(data, "Ach2", None),  # Second Aux channel voltage
    }

    with open(file_name, "w") as f:
        # Write header
        # f.write(f"{header}\n")
        # Write data
        for i in range(len(data.t)):
            line = f"{gamry_data['Time'][i]},{gamry_data['Vf'][i]},{gamry_data['Vu'][i]},{gamry_data['Vsig'][i]},"
            line += f"{gamry_data['Ach'] if gamry_data['Ach'] is not None else 'N/A'},"
            line += f"{gamry_data['Overload'] if gamry_data['Overload'] is not None else 'N/A'},"
            line += f"{gamry_data['StopTest'] if gamry_data['StopTest'] is not None else 'N/A'},"
            line += (
                f"{gamry_data['Temp'] if gamry_data['Temp'] is not None else 'N/A'}\n"
            )
            f.write(line)


# =====================
# Helper functions
# =====================


def setfilename(
    experiment_id,
    experiment_type,
    data_dir,
    project_campaign_id: int = None,
    campaign_id: int = None,
    well_id: str = None,
) -> pathlib.Path:
    """set the file name for the experiment"""
    global COMPLETE_FILE_NAME
    if project_campaign_id is None and campaign_id is None and well_id is None:
        file_name = f"{experiment_id}_{experiment_type}"
        file_name = file_name.replace(" ", "_")
        file_name_start = file_name + "_0"
        filepath: pathlib.Path = (data_dir / file_name_start).with_suffix(".txt")
        i = 1
        while filepath.exists():
            next_file_name = f"{file_name}_{i}"
            filepath = pathlib.Path(data_dir / str(next_file_name)).with_suffix(".txt")
            i += 1
    else:
        file_name = f"{project_campaign_id}_{campaign_id}_{experiment_id}_{well_id}_{experiment_type}"
        file_name = file_name.replace(" ", "_")
        file_name_start = file_name + "_0"
        filepath: pathlib.Path = (data_dir / file_name_start).with_suffix(".txt")
        # Check if the file already exists. If it does then add a number to the end of the file name
        i = 1
        while filepath.exists():
            next_file_name = f"{file_name}_{i}"
            filepath = pathlib.Path(data_dir / str(next_file_name)).with_suffix(".txt")
            i += 1
    COMPLETE_FILE_NAME = str(filepath)
    return COMPLETE_FILE_NAME


def pstat_connect():
    pass


def pstat_disconnect():
    pass


def active_check():
    pass


def check_vf_range(filename) -> Tuple[bool, float]:
    """Check if the Vf value is in the valid range for an echem experiment."""
    try:
        ocp_data = pd.read_csv(
            filename,
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        vf_last_row_scientific = ocp_data.iloc[-2, ocp_data.columns.get_loc("Vf")]
        logger.debug("Vf last row (sci): %.2E", Decimal(vf_last_row_scientific))
        vf_last_row_decimal = float(vf_last_row_scientific)
        logger.debug("Vf last row (float): %f", vf_last_row_decimal)

        if -1 < vf_last_row_decimal and vf_last_row_decimal < 1:
            logger.debug("Vf in valid range (-1 to 1). Proceeding to echem experiment")
            return True, vf_last_row_decimal
        else:
            logger.error("Vf not in valid range. Aborting echem experiment")
            return False, 0.0
    except Exception as error:
        logger.error("Error occurred while checking Vf: %s", error)
        return False, 0.0
