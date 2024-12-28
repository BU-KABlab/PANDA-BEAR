"""Useful functions and dataclasses for the project."""

import dataclasses
import tkinter as tk
from enum import Enum
from tkinter import filedialog

import pulp


class WellStatus(Enum):
    """Class for naming of the well status."""

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
    """Class for storing coordinates."""

    def __init__(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    @property
    def x(self):
        """Getter for the x-coordinate."""
        return round(float(self._x), 6)

    @x.setter
    def x(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("x-coordinate must be an int, or float")
        self._x = round(value, 6)

    @property
    def y(self):
        """Getter for the y-coordinate."""
        return round(float(self._y), 6)

    @y.setter
    def y(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("y-coordinate must be an int, float, or Decimal object")
        self._y = round(value, 6)

    @property
    def z(self):
        """Getter for the z-coordinate."""
        return round(float(self._z), 6)

    @z.setter
    def z(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("z-coordinate must be an int, float, or Decimal object")
        self._z = round(value, 6)


class Instruments(Enum):
    """Class for naming of the mill instruments."""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"
    DECAPPER = "decapper"


class SystemState(Enum):
    """Class for naming of the system states."""

    STARTUP = "startup"
    PIPETTE_PURGE = "pipette_purge"
    EXPERIMENT_LOOKUP = "experiment_lookup"
    IDLE = "idle"
    BUSY = "running"
    RUNNING = "running"
    ERROR = "error"
    ON = "on"
    OFF = "off"
    TESTING = "testing"
    CALIBRATING = "calibrating"
    SHUTDOWN = "shutdown"
    PAUSE = "pause"
    RESUME = "resume"
    WAITING = "waiting"
    STOP = "stop"


@dataclasses.dataclass
class ProtocolEntry:
    """Class for storing protocol entries."""

    protocol_id: int
    project: str
    name: str
    filepath: str

    def __str__(self):
        return f"{self.protocol_id}: {self.name}"


def solve_vials_ilp(
    vial_concentration_map: dict[str, float], v_total: float, c_target: float
) -> tuple[dict[str, float], float, dict[str, float]]:
    """
    Solve the concentration mixing problem using integer linear programming.

    Parameters
    ----------
    C : dict of str,floats - Concentrations of each vial in mM, keyed by vial_position.
    V_total : float - Total volume to achieve in uL.
    C_target : float - Target concentration in mM.

    Returns
    -------
    vial_volumes : dict of str,floats - Volumes of each concentration to achieve the target.
    deviation_value : float - Deviation from the target concentration in mM.
    vial_vol_by_location : dict of str,floats - Volumes of each vial to achieve the target.
    """
    if len(vial_concentration_map) == 1:
        deviation_value = abs(next(iter(vial_concentration_map.values())) - c_target)
        if deviation_value == 0:
            vial_vol_by_conc = {next(iter(vial_concentration_map.keys())): v_total}
            vial_vol_by_location = {
                position: v_total for position in vial_concentration_map
            }
        else:
            vial_vol_by_conc = None
            vial_vol_by_location = None
        return vial_vol_by_conc, deviation_value, vial_vol_by_location

    # Validate and clean the incoming data to remove any Decimal objects
    vial_concentration_map = {k: float(v) for k, v in vial_concentration_map.items()}
    vial_concentrations = [
        vial_concentration_map[position] for position in vial_concentration_map
    ]
    v_total = float(v_total)
    c_target = float(c_target)

    # Before solving the problem, check if the target concentration is already achievable with the given vials
    if c_target in vial_concentrations:
        vial_with_target_concentration = next(
            (
                position
                for position, concentration in vial_concentration_map.items()
                if concentration == c_target
            ),
            None,
        )
        if vial_with_target_concentration:
            vial_vol_by_conc = {c_target: v_total}
            vial_vol_by_location = {
                position: v_total for position in vial_concentration_map
            }
            for position in vial_concentration_map:
                # Set the volume of all vials to 0 except the vial with the target concentration
                if position != vial_with_target_concentration:
                    vial_vol_by_location[position] = 0
            deviation_value = 0
            return vial_vol_by_conc, deviation_value, vial_vol_by_location
        else:
            vial_vol_by_conc = None
            deviation_value = None
            vial_vol_by_location = None
            return vial_vol_by_conc, deviation_value, vial_vol_by_location

    # Create a problem instance
    prob = pulp.LpProblem("VialMixing", pulp.LpMinimize)

    # Define variables:
    # volumes for each vial (integer), binary variables, and deviation (continuous)
    v_vars = {
        f"C{concentration}": pulp.LpVariable(
            f"C{concentration}", lowBound=0, upBound=200, cat="Continuous"
        )
        for concentration in vial_concentrations
    }
    b_vars = [
        pulp.LpVariable(f"B{position}", cat="Binary")
        for position in vial_concentration_map
    ]
    c_deviation = pulp.LpVariable("deviation", lowBound=0, cat="Continuous")

    # Objective function: Minimize the deviation
    prob += c_deviation

    # Constraints
    prob += (
        pulp.lpSum(
            [
                concentration * v_vars[f"C{concentration}"]
                for concentration in vial_concentrations
            ]
        )
        == c_target * v_total,
        "ConcentrationConstraint",
    )
    prob += pulp.lpSum(v_vars.values()) == v_total, "VolumeConstraint"
    prob += (
        pulp.lpSum(
            [
                concentration * v_vars[f"C{concentration}"]
                for concentration in vial_concentrations
            ]
        )
        - c_target * v_total
        <= c_deviation,
        "PositiveDeviation",
    )
    prob += (
        -pulp.lpSum(
            [
                concentration * v_vars[f"C{concentration}"]
                for concentration in vial_concentrations
            ]
        )
        + c_target * v_total
        <= c_deviation,
        "NegativeDeviation",
    )

    # Additional constraints to enforce volume values
    for i, concentration in enumerate(vial_concentrations):
        prob += (
            v_vars[f"C{concentration}"] >= 20 * b_vars[i],
            f"LowerBoundConstraint{i}",
        )
        prob += (
            v_vars[f"C{concentration}"] <= 120 * b_vars[i],
            f"UpperBoundConstraint{i}",
        )

    # Solve the problem
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    if prob.status == pulp.LpStatusOptimal:
        vial_vol_by_conc = {
            concentration: round(pulp.value(v_vars[f"C{concentration}"]), 2)
            for concentration in vial_concentrations
        }  # Round to the nearest hundredth

        vial_vol_by_location = {
            position: round(
                pulp.value(v_vars[f"C{vial_concentration_map[position]}"]), 2
            )
            for position in vial_concentration_map
        }
        deviation_value = pulp.value(c_deviation)
        return vial_vol_by_conc, deviation_value, vial_vol_by_location
    else:
        return None, None, None


def file_picker(file_types=None):
    """Open a file picker dialog and return the selected file path."""
    if file_types is None:
        file_types = [("CSV", "*.csv")]
    elif isinstance(file_types, str):
        file_types = [(file_types.upper(), f"*.{file_types.lower()}")]
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(filetypes=file_types)
    root.destroy()
    return file_path


def directory_picker():
    """Open a directory picker dialog and return the selected directory path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    directory_path = filedialog.askdirectory()
    root.destroy()
    return directory_path


def input_validation(
    prompt: str,
    valid_types: tuple | type | list,
    value_range: tuple = None,
    allow_blank: bool = True,
    custom_error: str = None,
    menu_items: list = None,
    exit_option: bool = False,
):
    """Prompt the user for input and validate the input type."""

    error_message = (
        custom_error if custom_error else "Invalid input type. Please try again."
    )

    if exit_option:
        prompt += " (Type 'exit' to exit the program)"
        if menu_items:
            menu_items.append("exit")

    while True:
        try:
            user_input = input(prompt).strip()
            if not user_input and allow_blank:
                return None

            if exit_option and user_input.lower() == "exit":
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
            if value_range and not (
                value_range[0] <= converted_input <= value_range[1]
            ):
                raise ValueError(
                    f"Input must be between {value_range[0]} and {value_range[1]}."
                )

            # Check if the converted input is in the specified menu items
            # But first lowercase all menu items and the converted input
            if menu_items and valid_types is str:
                menu_items = [item.lower() for item in menu_items]
                converted_input = converted_input.lower()
            if menu_items and converted_input not in menu_items:
                # turn menu items into strings
                menu_items_str = [str(item) for item in menu_items]
                raise ValueError(
                    f"Input must be one of the following: {', '.join(menu_items_str)}."
                )

            return converted_input

        except ValueError as e:
            print(e)


if __name__ == "__main__":
    mapped_vials = {"S1": 100, "S2": 50, "S3": 25}  # location: concentration
    desired_volume = 100
    desired_concentration = 75
    volumes, deviation, locations = solve_vials_ilp(
        mapped_vials, desired_volume, desired_concentration
    )

    print(
        f"""
    Possible Vials (Location: Concentration): {mapped_vials}
    Target Volume: {desired_volume}
    Target Concentration: {desired_concentration}
    -------------------------
    Volumes per concentration (concentration:volume): {volumes}

    Deviation from target concentration: {deviation}

    Volumes per location (location:volume): {locations}

"""
    )
    position = "S2"
    volume_for_position = next((v for k, v in locations.items() if k == position), None)
    print(volume_for_position)
