"""A class to hold all of the instruments"""

from dataclasses import dataclass
from logging import Logger
from typing import Union

import PySpin

from hardware.pipette.syringepump import MockPump, SyringePump
from hardware.sartorius.sartorius import Scale
from hardware.sartorius.sartorius.mock import Scale as MockScale
from panda_lib.labware.vials import StockVial, WasteVial, read_vials
from panda_lib.labware.wellplate import Wellplate
from panda_lib.obs_controls import OBSController

# from panda_lib.movement import Mill, MockMill
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.slack_tools.SlackBot import SlackBot
from panda_lib.tools.pawduino import ArduinoLink


@dataclass
class Toolkit:
    """A class to hold all of the instruments"""

    mill: Union[Mill, MockMill, None]
    scale: Union[Scale, MockScale, None]
    pump: Union[SyringePump, MockPump, None]
    wellplate: Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
    flir_camera: PySpin.Camera = None
    arduino: ArduinoLink = None


@dataclass
class Hardware:
    """A class to hold all of the hawrdware"""

    mill: Union[Mill, MockMill, None] = None
    scale: Union[Scale, MockScale, None] = None
    pump: Union[SyringePump, MockPump, None] = None
    flir_camera: PySpin.Camera = None
    arduino: ArduinoLink = None
    # inlcude the global logger so that the hardware can log to the same file
    global_logger: Logger = None
    experiment_logger: Logger = None


@dataclass
class Labware:
    """A class to hold all of the labware"""

    wellplate: Wellplate = None
    # include the global logger so that the labware can log to the same file
    global_logger: Logger = None

    @property
    def stock_vials(self) -> list[StockVial]:
        return read_vials("stock")[0]  # TODO: Fix this

    @property
    def waste_vials(self) -> list[WasteVial]:
        return read_vials("waste")[0]  # TODO: Fix this


@dataclass
class Monitoring:
    """A class to hold all of the monitoring tools"""

    slack_monitor: SlackBot = None
    obs: OBSController = None
