"""A class to hold all of the instruments"""
from dataclasses import dataclass
from logging import Logger
from typing import Union

from panda_lib.mill_control import Mill, MockMill
from panda_lib.syringepump import MockPump, SyringePump
from sartorius.sartorius import Scale
from sartorius.sartorius.mock import Scale as MockScale
import panda_lib.wellplate as wp
import PySpin
from pawduino import ArduinoLink

@dataclass
class Toolkit:
    """A class to hold all of the instruments"""

    mill: Union[Mill, MockMill, None]
    scale: Union[Scale, MockScale, None]
    pump: Union[SyringePump, MockPump, None]
    wellplate: wp.Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
    flir_camera: PySpin.Camera = None
    arduino: ArduinoLink = None
