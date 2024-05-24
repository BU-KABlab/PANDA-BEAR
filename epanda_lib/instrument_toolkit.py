"""A class to hold all of the instruments"""
from dataclasses import dataclass
from logging import Logger
from typing import Union

from epanda_lib.mill_control import Mill, MockMill
from epanda_lib.pump_control import MockPump, Pump
from epanda_lib.sartorius_local import Scale
from epanda_lib.sartorius_local.mock import Scale as MockScale
import epanda_lib.wellplate as wp


@dataclass
class Toolkit:
    """A class to hold all of the instruments"""

    mill: Union[Mill, MockMill]
    scale: Union[Scale, MockScale]
    pump: Union[Pump, MockPump]
    wellplate: wp.Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
