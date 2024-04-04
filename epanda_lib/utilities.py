"""Useful functions and dataclasses for the project."""

import dataclasses
from enum import Enum

import pulp


@dataclasses.dataclass
class Coordinates:
    """Class for storing coordinates"""

    x: float
    y: float
    z: float

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"


@dataclasses.dataclass
class Instruments(Enum):
    """Class for naming of the mill instruments"""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"


@dataclasses.dataclass
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


@dataclasses.dataclass
class ProtocolEntry:
    """Class for storing protocol entries"""

    protocol_id: int
    project: str
    name: str
    filepath: str

    def __str__(self):
        return f"{self.protocol_id}: {self.name}"


def solve_vials_ilp(vial_concentrations:list, v_total:float, c_target:float):
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
    
    # Create a problem instance
    prob = pulp.LpProblem("VialMixing", pulp.LpMinimize)
    
    # Define variables: volumes for each vial (integer), binary variables, and deviation (continuous)
    v_vars = [pulp.LpVariable(f"V{i}", lowBound=0, upBound=200, cat='Continuous') for i in range(num_vials)]
    b_vars = [pulp.LpVariable(f"B{i}", cat='Binary') for i in range(num_vials)]
    c_deviation = pulp.LpVariable("deviation", lowBound=0, cat='Continuous')
    
    # Objective function: Minimize the deviation
    prob += c_deviation
    
    # Constraints
    prob += pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)]) == c_target * v_total, "ConcentrationConstraint"
    prob += pulp.lpSum(v_vars) == v_total, "VolumeConstraint"
    prob += pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)]) - c_target * v_total <= c_deviation, "PositiveDeviation"
    prob += -pulp.lpSum([vial_concentrations[i] * v_vars[i] for i in range(num_vials)]) + c_target * v_total <= c_deviation, "NegativeDeviation"
    
    # Additional constraints to enforce volume values
    for i in range(num_vials):
        prob += v_vars[i] >= 20 * b_vars[i], f"LowerBoundConstraint{i}"
        prob += v_vars[i] <= 120 * b_vars[i], f"UpperBoundConstraint{i}"
    
    # Solve the problem
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    if prob.status == pulp.LpStatusOptimal:
        vial_volumes = [round(pulp.value(v_vars[i]), 2) for i in range(num_vials)]  # Round to the nearest hundredth
        deviation_value = pulp.value(c_deviation)
        return vial_volumes, deviation_value
    else:
        return None, None


if __name__ == "__main__":
    C = [10, 20]  # Concentrations of each vial in mM
    V_total = 120  # Total volume to achieve in uL
    C_target = 15  # Target concentration in mM

    volumes, deviation = solve_vials_ilp(C, V_total, C_target)
    if volumes is not None:
        print(f"Volumes to draw from each vial: {volumes} uL")
        print(f"Deviation from target concentration: {deviation} mM")
    else:
        print("No solution found")
