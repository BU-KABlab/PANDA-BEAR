from typing import Dict, Tuple, TypedDict, Literal, Any, Protocol
import json

# Common type aliases
Coordinates = Dict[str, float]
ToolOffset = Tuple[float, float, float]
ChemicalContents = Dict[str, float]
WellID = str
PlateID = int
TipID = str
TipRackID = str

# Status types
ExperimentStatusType = Literal["new", "ready", "running", "done", "error", "cancelled"]
WellStatusType = Literal["new", "used", "reserved", "error"]
TipStatusType = Literal["new", "used", "reserved", "error"]


# Common structures
class CoordinatesDict(TypedDict):
    x: float
    y: float
    z: float


# Vial and Well related types
class WellKwargs(TypedDict, total=False):
    """
    TypedDict for Well constructor keyword arguments

    Attributes:
        name (str): Name of the well
        volume (float): Volume of the well
        capacity (float): Capacity of the well
        height (float): Height of the well
        radius (float): Radius of the well
        contamination (int): Contamination level
        dead_volume (float): Dead volume in the well
        contents (Dict[str, float]): Chemical contents in the well
        coordinates (Dict[str, float]): Coordinates of the well

    """

    name: str
    volume: float
    capacity: float
    height: float
    radius: float
    contamination: int
    dead_volume: float
    contents: Dict[str, float]
    coordinates: CoordinatesDict


class VialKwargs(TypedDict, total=False):
    """TypedDict for Vial constructor keyword arguments"""

    category: int
    height: float
    radius: float
    volume: float
    capacity: float
    contamination: int
    dead_volume: float
    contents: Dict[str, float]
    viscosity_cp: float
    concentration: float
    density: float
    coordinates: Dict[str, float]
    name: str
    base_thickness: float


class TipKwargs(TypedDict, total=False):
    """TypedDict for Tip constructor keyword arguments"""

    name: str
    capacity: float
    coordinates: CoordinatesDict
    pickup_height: float


# Hardware types
class PipetteState(TypedDict):
    """TypedDict for PipetteState"""

    capacity_ul: float
    capacity_ml: float
    volume: float
    volume_ml: float
    contents: Dict[str, Any]


# Experiment related types
class ExperimentParameter(TypedDict):
    """TypedDict for experiment parameters"""

    experiment_id: int
    parameter_name: str
    parameter_value: Any


# Tool related types
class ToolInfo(TypedDict):
    """TypedDict for tool information"""

    name: str
    x: float
    y: float
    z: float


# Protocol for JSON serialization
class JSONSerializable(Protocol):
    """Protocol for objects that can be serialized to JSON"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary for JSON serialization"""
        ...


def deserialize_json(json_string: str) -> Dict[str, Any]:
    """Helper function to deserialize JSON string to dictionary"""
    if not json_string:
        return {}
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {}
