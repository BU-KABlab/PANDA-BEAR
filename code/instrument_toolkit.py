"""A class to hold all of the instruments"""
from dataclasses import dataclass
from logging import Logger
from typing import Union

from mill_control import Mill, MockMill
from pump_control import MockPump, Pump
from sartorius_local import Scale
from sartorius_local.mock import Scale as MockScale
from wellplate import Wellplate


@dataclass
class Toolkit:
    """A class to hold all of the instruments"""

    mill: Union[Mill, MockMill]
    scale: Union[Scale, MockScale]
    pump: Union[Pump, MockPump]
    wellplate: Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
