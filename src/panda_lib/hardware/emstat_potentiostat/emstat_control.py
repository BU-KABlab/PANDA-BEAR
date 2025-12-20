import hardpotato as hp
from panda_shared.config import read_data_dir
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
import pathlib
import logging
from typing import Tuple
import pandas as pd
import inspect

global COMPLETE_FILE_NAME
logger = logging.getLogger("panda")

# ========
# Helpers
# ========


def _as_dict_like(params):
    """Return a (key->value) mapping from params which may be a dict or object."""
    if isinstance(params, dict):
        return dict(params)
    # object with attributes
    return {
        k: getattr(params, k)
        for k in dir(params)
        if not k.startswith("_") and hasattr(params, k)
    }


def _coerce_float(v):
    try:
        return float(v)
    except Exception:
        return v


def _coerce_int(v):
    try:
        return int(v)
    except Exception:
        return v


def _normalize_cv_kwargs(params):
    """
    Accepts cv_parameters | dict | any attr object.
    Returns kwargs filtered to what hp.potentiostat.CV accepts.
    Handles common alias names (Gamry-style -> EmStat-style).
    """
    raw = _as_dict_like(params)

    aliases = {
        "CVvi": "Eini",
        "CVap1": "Ev1",
        "CVap2": "Ev2",
        "CVvf": "Efin",
        "sr1": "sr",
        "sr2": "sr",
        "sr3": "sr",
        "nCycles": "nSweeps",
        "cycleCount": "nSweeps",
        "step": "dE",
        "step_size": "dE",
        "file_stem": "fileName",
        "filename": "fileName",
        "name": "fileName",
        "title": "header",
    }

    for old, new in list(aliases.items()):
        if old in raw and new not in raw:
            raw[new] = raw.pop(old)

    # Coerce core fields to numeric types if present
    numeric_float_keys = (
        "Eini",
        "Ev1",
        "Ev2",
        "Efin",
        "sr",
        "dE",
        "sens",
        "sens2",
        "E2",
    )
    for k in numeric_float_keys:
        if k in raw and raw[k] is not None:
            raw[k] = _coerce_float(raw[k])

    numeric_int_keys = ("nSweeps",)
    for k in numeric_int_keys:
        if k in raw and raw[k] is not None:
            raw[k] = _coerce_int(raw[k])

    # Filter to CV.__init__ signature
    sig = inspect.signature(hp.potentiostat.CV.__init__)
    allowed = {name for name in sig.parameters if name != "self"}

    kwargs = {k: v for k, v in raw.items() if (v is not None and k in allowed)}

    # Optionally enforce a minimal set that EmStat needs
    required = {
        "Eini",
        "Ev1",
        "Ev2",
        "Efin",
        "sr",
        "dE",
        "nSweeps",
        "fileName",
        "header",
    }
    missing = [k for k in required if k not in kwargs]
    if missing:
        # You may prefer to log a warning and fill defaults instead of raising
        raise ValueError(f"Missing required EmStat CV parameters: {missing}")

    return kwargs


# =====================
# Parameter dataclasses
# =====================


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ocp_parameters:
    """Parameters for Open Circuit Potential (OCP) experiment.
    This class defines the parameters needed to run an OCP experiment
    on the EmStat Pico potentiostat.

    Attributes:
        ttot (float): Total time for the experiment in seconds.
        dt (float): Time increment in seconds.
        fileName (str): Base file name for data file.
        header (str): Header for data file."""

    ttot: float = 1  # s, total time
    dt: float = 0.01  # s, time increment
    fileName: str = "OCP"  # base file name for data file
    header: str = "OCP"  # header for data file


@dataclass(config=ConfigDict(validate_assignment=True))
class cv_parameters:
    """Parameters for Cyclic Voltammetry experiment.
    This class defines the parameters needed to run a cyclic voltammetry experiment
    on the EmStat Pico potentiostat.

    Attributes:
        Eini (float): Initial potential in volts.
        Ev1 (float): First vertex potential in volts.
        Ev2 (float): Second vertex potential in volts.
        Efin (float): Final potential in volts.
        sr (float): Scan rate in V/s.
        dE (float): Potential increment in volts.
        nSweeps (int): Number of sweeps.
        sens (float): Current sensitivity in A/V.
        E2 (float): Potential of the second working electrode in volts.
        sens2 (float): Current sensitivity of the second working electrode in A/V.
        fileName (str): Base file name for data file.
        header (str): Header for data file."""

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
class chrono_parameters:
    """Parameters for Chronoamperometry experiment.

    This class defines the parameters needed to run a chronoamperometry experiment
    on the EmStat Pico potentiostat.

    Attributes:
        Estep (float): Step potential in volts.
        dt (float): Time increment in seconds.
        ttot (float): Total time for the experiment in seconds.
        sens (float): Current sensitivity in A/V.
        E2 (float): Potential of the second working electrode in volts.
        sens2 (float): Current sensitivity of the second working electrode in A/V.
        fileName (str): Base file name for the data file.
        header (str): Header for the data file."""

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


def OCP(params: potentiostat_ocp_parameters):
    """Run OCP experiment on EmStat"""
    model = "emstat4_lr"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    connected = setup.check_connection()
    if not connected:
        raise RuntimeError("Could not connect to Pstat")
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    file_stem = pathlib.Path(COMPLETE_FILE_NAME).stem
    ocp = hp.potentiostat.OCP(params.ttot, params.dt, file_stem, params.header)
    ocp.run()
    # save_in_gamry_format(ocp.data, COMPLETE_FILE_NAME, params.header)
    return ocp.data


def OCP_check(params: potentiostat_ocp_parameters):
    """Run OCP experiment on EmStat"""
    model = "emstat4_lr"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    connected = setup.check_connection()
    if not connected:
        raise RuntimeError("Could not connect to Pstat")
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    file_stem = pathlib.Path(COMPLETE_FILE_NAME).stem
    ocp = hp.potentiostat.OCP(params.ttot, params.dt, file_stem, params.header)
    ocp.run()
    # save_in_gamry_format(ocp.data, COMPLETE_FILE_NAME, params.header)
    return ocp.data


def cyclic(params: cv_parameters | dict):
    """Run CV experiment on EmStat (accepts dataclass OR dict)."""
    model = "emstat4_lr"
    folder = read_data_dir()
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    if not setup.check_connection():
        raise RuntimeError("Could not connect to Pstat")

    global COMPLETE_FILE_NAME
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    file_stem = pathlib.Path(COMPLETE_FILE_NAME).stem

    if isinstance(params, dict):
        params = {**params, "fileName": file_stem, "header": "CV"}
    else:
        if not getattr(params, "fileName", None):
            setattr(params, "fileName", file_stem)
        if not getattr(params, "header", None):
            setattr(params, "header", "CV")

    kwargs = _normalize_cv_kwargs(params)
    if "nSweeps" in kwargs:
        kwargs["nSweeps"] = int(kwargs["nSweeps"])

    logger.debug("EmStat CV kwargs: %s", kwargs)

    try:
        cv = hp.potentiostat.CV(**kwargs)
    except TypeError:
        logger.error("Failed to construct CV with kwargs=%s", kwargs)
        raise

    cv.run()
    return cv.data


'''
Saving to verify new function works before replacing old one
def cyclic(params: cv_parameters):
    """Run CV experiment on EmStat"""
    model = "emstat4_lr"
    folder = read_data_dir()
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    connected = setup.check_connection()
    if not connected:
            raise RuntimeError("Could not connect to Pstat")
    global COMPLETE_FILE_NAME
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    file_stem = pathlib.Path(COMPLETE_FILE_NAME).stem
    cv = hp.potentiostat.CV(
        Eini=params.Eini,
        Ev1=params.Ev1,
        Ev2=params.Ev2,
        Efin=params.Efin,
        sr=params.sr,
        dE=params.dE,
        nSweeps=params.nSweeps,
        sens=params.sens,
        E2=params.E2,
        sens2=params.sens2,
        fileName=file_stem,
        header=params.header,
    )
    cv.run()
    # save_in_gamry_format(cv.data, COMPLETE_FILE_NAME, params.header)
    return cv.data
'''


def chrono(params: chrono_parameters):
    """Run CA experiment on EmStat."""
    model = "emstat4_lr"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    connected = setup.check_connection()
    if not connected:
        raise RuntimeError("Could not connect to Pstat")

    ca = hp.potentiostat.CA(
        Estep=params.Estep,
        dt=params.dt,
        ttot=params.ttot,
        sens=params.sens,
        fileName=pathlib.Path(
            COMPLETE_FILE_NAME
        ).stem,  # Use the stem of the path to avoid double extension
        header=params.header,
        E2=params.E2,  # if your subclass needs it
        sens2=params.sens2,  # if your subclass needs it
    )

    ca.run()
    # save_in_gamry_format(ca.data, COMPLETE_FILE_NAME, params.header)
    return ca.data


def run_mscript(params: MScriptParameters):
    """Run custom mscript file on EmStat."""
    model = "emstat4_lr"
    folder = read_data_dir()
    global COMPLETE_FILE_NAME
    setup = hp.potentiostat.Setup(model, None, folder, verbose=0)
    connected = setup.check_connection()
    if not connected:
        raise RuntimeError("Could not connect to Pstat")
    COMPLETE_FILE_NAME = validate_file_name(COMPLETE_FILE_NAME)
    mscript = hp.potentiostat.MethodScript(
        None,
        None,
        params.script_path,
    )
    mscript.run()
    return mscript.data
    # save_in_gamry_format(data, COMPLETE_FILE_NAME, params.header)


# =====================
# Data saving utility
# =====================
def save_in_gamry_format(data, file_name: str, header: str):
    """
    Save Hardpotato data (as a list of dicts) in a format similar to Gamry:
    ["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "Overload", "StopTest", "Cycle", "Ach2"]
    """
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Data must be a non-empty list of dictionaries")

    with open(file_name, "w") as f:
        # Write header row (optional)
        # f.write(f"{header}\n")

        for row in data:
            line = ",".join(
                str(row.get(key, "N/A"))
                for key in [
                    "t",
                    "E",
                    "U",
                    "I",
                    "Vsig",
                    "Ach",
                    "Overload",
                    "StopTest",
                    "Cycle",
                    "Ach2",
                ]
            )
            f.write(line + "\n")


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


def pstatconnect():
    pass


def pstatdisconnect():
    pass


def activecheck():
    pass


def check_vf_range(filename) -> Tuple[bool, float]:
    """Check if the Vf value is in the valid range for an echem experiment."""
    try:
        # Read with a tolerant parser:
        # - treat '#' as comments
        # - allow commas OR whitespace as separators
        # - force exactly two columns (Time, Vf)
        ocp_data = pd.read_csv(
            filename,
            comment="#",
            header=None,
            names=["Time", "Vf"],
            usecols=[0, 1],
            sep=r"\s*,\s*|\s+",
            engine="python",
            skip_blank_lines=True,
        )

        # Ensure numeric; drop any rows that failed to parse
        ocp_data["Time"] = pd.to_numeric(ocp_data["Time"], errors="coerce")
        ocp_data["Vf"] = pd.to_numeric(ocp_data["Vf"], errors="coerce")
        ocp_data = ocp_data.dropna(subset=["Time", "Vf"])

        if ocp_data.empty:
            raise ValueError(f"OCP file has no numeric data: {filename}")

        vf_last_row_decimal = float(ocp_data["Vf"].iloc[-1])
        # Scientific + float logs (no Decimal required)
        # logger.debug("Vf last row (sci): %.2E", vf_last_row_decimal)
        # logger.debug("Vf last row (float): %f", vf_last_row_decimal)

        if 0.001 < abs(vf_last_row_decimal) < 0.5:
            # logger.debug("Vf in valid range (0.001 to 0.5). Proceeding to echem experiment")
            return True, vf_last_row_decimal
        else:
            # logger.error("Vf not in valid range. Aborting echem experiment")
            return False, 0.0

    except Exception:
        # logger.error("Error occurred while checking Vf: %s", error)
        return False, 0.0
