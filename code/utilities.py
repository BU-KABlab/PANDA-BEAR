"""Useful functions and dataclasses for the project."""
import dataclasses
from enum import Enum

@dataclasses.dataclass
class Coordinates:
    """Class for storing coordinates"""

    x: float
    y: float
    z: float


@dataclasses.dataclass
class Instruments(Enum):
    """Class for naming of the mill instruments"""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"
