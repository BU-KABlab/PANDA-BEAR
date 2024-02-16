"""Class of the instruments used on the CNC mill."""
import dataclasses
from enum import Enum

@dataclasses.dataclass
class Instruments(Enum):
    """Class for naming of the mill instruments"""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"
