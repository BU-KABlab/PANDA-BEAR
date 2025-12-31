from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
import numpy as np
import logging

# Set up logging for the mock
logging.basicConfig(level=logging.INFO)

# =====================
# Parameter dataclasses (same as real)
# =====================


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ocp_parameters:
    ttot: float = 1
    dt: float = 0.01
    fileName: str = "OCP"
    header: str = "OCP"


@dataclass(config=ConfigDict(validate_assignment=True))
class cv_parameters:
    Eini: float = -0.5
    Ev1: float = 0.5
    Ev2: float = -0.5
    Efin: float = -0.5
    sr: float = 1
    dE: float = 0.001
    nSweeps: int = 2
    sens: float = 1e-6
    E2: float = 0.5
    sens2: float = 1e-9
    fileName: str = "CV"
    header: str = "CV"


@dataclass(config=ConfigDict(validate_assignment=True))
class chrono_parameters:
    Estep: float = 0.5
    dt: float = 0.01
    ttot: float = 1
    sens: float = 1e-6
    E2: float = 0.5
    sens2: float = 1e-9
    fileName: str = "CA"
    header: str = "CA"


@dataclass(config=ConfigDict(validate_assignment=True))
class MScriptParameters:
    script_path: str
    fileName: str = "MSCRIPT"
    header: str = "MSCRIPT"


def validate_file_name(file_name: str) -> str:
    if not file_name.endswith((".txt", ".csv")):
        file_name += ".txt"
    return file_name


# =====================
# Mock Experiment functions
# =====================


def OCP(params: potentiostat_ocp_parameters):
    logging.info(f"[MOCK] Running OCP with params: {params}")
    data = DummyData(params.ttot, params.dt)
    save_in_gamry_format(data, validate_file_name(params.fileName), params.header)


def cyclic(params: cv_parameters):
    logging.info(f"[MOCK] Running CV with params: {params}")
    data = DummyData(
        2 * params.nSweeps * (params.Ev1 - params.Eini) / params.sr, params.dE
    )
    save_in_gamry_format(data, validate_file_name(params.fileName), params.header)


def chrono(params: chrono_parameters):
    logging.info(f"[MOCK] Running CA with params: {params}")
    data = DummyData(params.ttot, params.dt)
    save_in_gamry_format(data, validate_file_name(params.fileName), params.header)


def run_mscript(params: MScriptParameters):
    logging.info(
        f"[MOCK] Running MethodScript from {params.script_path} with params: {params}"
    )
    data = DummyData(1, 0.01)
    save_in_gamry_format(data, validate_file_name(params.fileName), params.header)


# =====================
# Dummy Data Generator
# =====================
class DummyData:
    def __init__(self, ttot, dt):
        self.t = np.arange(0, ttot, dt)
        self.E = np.sin(self.t)
        self.U = np.zeros_like(self.t)
        self.I = np.random.normal(0, 1e-6, size=self.t.shape)
        self.Vsig = np.ones_like(self.t)
        self.Ach = np.zeros_like(self.t)
        self.IERange = np.full_like(self.t, 1e-6)
        self.Overload = np.zeros_like(self.t)
        self.StopTest = np.zeros_like(self.t)
        self.Cycle = np.zeros_like(self.t)
        self.Ach2 = np.zeros_like(self.t)
        self.Temp = np.full_like(self.t, 25.0)


# =====================
# Data saving utility (mock)
# =====================
def save_in_gamry_format(data, file_name: str, header: str):
    logging.info(f"[MOCK] Saving data to {file_name} with header {header}")
    with open(file_name, "w") as f:
        # f.write(f"{header}\n")
        for i in range(len(data.t)):
            line = f"{data.t[i]},{data.E[i]},{data.U[i]},{data.Vsig[i]},"
            line += f"{data.Ach[i]},{data.Overload[i]},{data.StopTest[i]},{getattr(data, 'Temp', 'N/A')}\n"
            f.write(line)
