import hardpotato as hp
from panda_shared.config import read_data_dir
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

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
    model = 'emstatpico'
    folder = read_data_dir()
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    ocp = hp.potentiostat.OCP(
        params.ttot,
        params.dt,
        params.fileName,
        params.header
    )
    ocp.run()
    params.fileName = validate_file_name(params.fileName)
    data = hp.load_data.OCP(params.fileName, folder, model)
    save_in_gamry_format(data, params.fileName, params.header)

def cyclic(params: CVParameters):
    """Run CV experiment on EmStat Pico."""
    model = 'emstatpico'
    folder = read_data_dir()
    hp.potentiostat.Setup(model, None, folder, verbose=0)

    params.fileName = validate_file_name(params.fileName)
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
        params.fileName,
        params.header
    )
    cv.run()
    data = hp.load_data.CV(params.fileName, folder, model)
    save_in_gamry_format(data, params.fileName, params.header)
    

def chrono(params: CAParameters):
    """Run CA experiment on EmStat Pico."""
    model = 'emstatpico'
    folder = read_data_dir()
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    params.fileName = validate_file_name(params.fileName)
    ca = hp.potentiostat.CA(
        params.Estep,
        params.dt,
        params.ttot,
        params.sens,
        params.E2,
        params.sens2,
        params.fileName,
        params.header
    )
    ca.run()
    data = hp.load_data.CA(params.fileName, folder, model)
    save_in_gamry_format(data, params.fileName, params.header)

def run_mscript(params: MScriptParameters):
    """Run custom mscript file on EmStat Pico."""
    model = 'emstatpico'
    folder = read_data_dir()
    hp.potentiostat.Setup(model, None, folder, verbose=0)
    params.fileName = validate_file_name(params.fileName)
    mscript = hp.potentiostat.MethodScript(
        None,
        None,
        params.script_path,
    )
    mscript.run()
    data = hp.load_data.MethodScript(params.fileName, folder, model)
    save_in_gamry_format(data, params.fileName, params.header)

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
        "Vf": getattr(data, "E", None),    # Measured E vs. Eref
        "Vu": getattr(data, "U", None),    # Uncompensated voltage
        "Im": getattr(data, "I", None),    # Measured current
        "Vsig": getattr(data, "Vsig", None),  # Signal sent to Control Amp
        "Ach": getattr(data, "Ach", None),    # Measured Aux channel voltage
        "IERange": getattr(data, "IERange", None),  # Current range
        "Overload": getattr(data, "Overload", None),  # Overload status
        "StopTest": getattr(data, "StopTest", None),  # Stop flag
        "Cycle": getattr(data, "Cycle", None),        # Cycle number
        "Ach2": getattr(data, "Ach2", None),          # Second Aux channel voltage
    }

    with open(file_name, 'w') as f:
        # Write header
        #f.write(f"{header}\n")
        # Write data
        for i in range(len(data.t)):
            line = f"{gamry_data['Time'][i]},{gamry_data['Vf'][i]},{gamry_data['Vu'][i]},{gamry_data['Vsig'][i]},"
            line += f"{gamry_data['Ach'] if gamry_data['Ach'] is not None else 'N/A'},"
            line += f"{gamry_data['Overload'] if gamry_data['Overload'] is not None else 'N/A'},"
            line += f"{gamry_data['StopTest'] if gamry_data['StopTest'] is not None else 'N/A'},"
            line += f"{gamry_data['Temp'] if gamry_data['Temp'] is not None else 'N/A'}\n"
            f.write(line)