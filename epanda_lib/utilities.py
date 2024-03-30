"""Useful functions and dataclasses for the project."""
import dataclasses
from enum import Enum

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
    ON  = "on"
    OFF = "off"
    TESTING = "testing"
    CALIBRATING = "calibrating"

@dataclasses.dataclass
class ProtocolEntry:
    """Class for storing protocol entries"""

    protocol_id: int
    project: str
    name: str
    filepath: str

    def __str__(self):
        return f"{self.protocol_id}: {self.name}"
    