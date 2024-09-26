"""Useful functions and dataclasses for the project."""

import dataclasses
from decimal import Decimal
from enum import Enum
import tkinter as tk
from tkinter import filedialog


import pulp

class WellStatus(Enum):
    """Class for naming of the well status"""

    EMPTY = "empty"
    FILLED = "filled"
    MIXED = "mixed"
    ERROR = "error"
    BUSY = "running"
    ON = "on"
    OFF = "off"
    TESTING = "testing"
    CALIBRATING = "calibrating"
    SHUTDOWN = "shutdown"
    PAUSE = "pause"
    RESUME = "resume"
    WAITING = "waiting"

class Coordinates:
    """Class for storing coordinates"""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    @property
    def x(self):
        """Getter for the x-coordinate"""
        return round(float(self._x), 6)

    @x.setter
    def x(self, value):
        if isinstance(value, Decimal):
            value = float(value)
        elif not isinstance(value, (int, float)):
            raise ValueError(
                "x-coordinate must be an int, float, or Decimal object"
            )
        self._x = round(value, 6)

    @property
    def y(self):
        """Getter for the y-coordinate"""
        return round(float(self._y), 6)

    @y.setter
    def y(self, value):
        if isinstance(value, Decimal):
            value = float(value)
        elif not isinstance(value, (int, float)):
            raise ValueError(
                "y-coordinate must be an int, float, or Decimal object"
            )
        self._y = round(value, 6)

    @property
    def z(self):
        """Getter for the z-coordinate"""
        return round(float(self._z), 6)

    @z.setter
    def z(self, value):
        if isinstance(value, Decimal):
            value = float(value)
        elif not isinstance(value, (int, float)):
            raise ValueError(
                "z-coordinate must be an int, float, or Decimal object"
            )
        self._z = round(value, 6)


@dataclasses.dataclass
class Instruments(Enum):
    """Class for naming of the mill instruments"""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"


class SystemState(Enum):
    """Class for naming of the system states"""

    IDLE = "idle"
    BUSY = "running"
    ERROR = "error"
    ON = "on"
    OFF = "off"
    TESTING = "testing"
    CALIBRATING = "calibrating"
    SHUTDOWN = "shutdown"
    PAUSE = "pause"
    RESUME = "resume"
    WAITING = "waiting"


@dataclasses.dataclass
class ProtocolEntry:
    """Class for storing protocol entries"""

    protocol_id: int
    project: str
    name: str
    filepath: str

    def __str__(self):
        return f"{self.protocol_id}: {self.name}"


def solve_vials_ilp(vial_concentrations: list, v_total: float, c_target: float):
    """
    Solve the concentration mixing problem using integer linear programming.

    Parameters
    ----------
    C : list of float - Concentrations of each vial in mM.
    V_total : float - Total volume to achieve in uL.
    C_target : float - Target concentration in mM.

    Returns
    -------
    volumes : list of float - Volumes to draw from each vial in uL.
    deviation_value : float - Deviation from the target concentration in mM.
    """
    num_vials = len(vial_concentrations)

    # Validate and clean the incoming data to remove any Decimal objects
    vial_concentrations = [float(c) for c in vial_concentrations]
    v_total = float(v_total)
    c_target = float(c_target)

    # Create a problem instance
    prob = pulp.LpProblem("VialMixing", pulp.LpMinimize)

    # Define variables:
    # volumes for each vial (integer), binary variables, and deviation (continuous)
    v_vars = [
        pulp.LpVariable(f"V{i}", lowBound=0, upBound=200, cat="Continuous")
        for i in range(num_vials)
    ]
    b_vars = [pulp.LpVariable(f"B{i}", cat="Binary") for i in range(num_vials)]
    c_deviation = pulp.LpVariable("deviation", lowBound=0, cat="Continuous")

    # Objective function: Minimize the deviation
    prob += c_deviation

    # Constraints
    prob += (
        pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)])
        == c_target * v_total,
        "ConcentrationConstraint",
    )
    prob += pulp.lpSum(v_vars) == v_total, "VolumeConstraint"
    prob += (
        pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)])
        - c_target * v_total
        <= c_deviation,
        "PositiveDeviation",
    )
    prob += (
        -pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)])
        + c_target * v_total
        <= c_deviation,
        "NegativeDeviation",
    )

    # Additional constraints to enforce volume values
    for i in range(num_vials):
        prob += v_vars[i] >= 20 * b_vars[i], f"LowerBoundConstraint{i}"
        prob += v_vars[i] <= 120 * b_vars[i], f"UpperBoundConstraint{i}"

    # Solve the problem
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    if prob.status == pulp.LpStatusOptimal:
        vial_volumes = [
            round(pulp.value(v_vars[i]), 2) for i in range(num_vials)
        ]  # Round to the nearest hundredth
        deviation_value = pulp.value(c_deviation)
        return vial_volumes, deviation_value
    else:
        return None, None

# File picker
def file_picker(file_types=None):
    """Open a file picker dialog and return the selected file path."""
    if file_types is None:
        file_types = [("CSV", "*.csv")]
    elif isinstance(file_types, str):
        file_types = [(file_types.upper(), f"*.{file_types.lower()}")]
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(filetypes=file_types)
    root.destroy()
    return file_path

# Directory picker
def directory_picker():
    """Open a directory picker dialog and return the selected directory path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    directory_path = filedialog.askdirectory()
    root.destroy()
    return directory_path

def input_validation(prompt:str, valid_types:tuple|type|list, value_range:tuple=None, allow_blank:bool = True, custom_error:str=None):
    """Prompt the user for input and validate the input type."""

    error_message = custom_error if custom_error else "Invalid input type. Please try again."

    while True:
        try:
            user_input = input(prompt)
            if not user_input and allow_blank:
                return None

            # Attempt to convert the input to each of the valid types
            if isinstance(valid_types, (tuple, list)):
                for valid_type in valid_types:
                    try:
                        converted_input = valid_type(user_input)
                        break
                    except (ValueError, TypeError):
                        continue
                else:
                    raise ValueError(error_message)
            else:
                converted_input = valid_types(user_input)

            # Check if the converted input is within the specified range
            if value_range and not (value_range[0] <= converted_input <= value_range[1]):
                raise ValueError(f"Input must be between {value_range[0]} and {value_range[1]}.")

            return converted_input

        except ValueError as e:
            print(e)
