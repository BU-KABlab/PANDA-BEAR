import panda_lib
from panda_lib.hardware import ArduinoLink, PandaMill, Scale
from panda_lib.hardware.panda_pipettes import Pipette
from panda_lib.toolkit import Toolkit

tools = Toolkit(
    mill=PandaMill(), arduino=ArduinoLink("dev/ttyACM1"), scale=Scale("dev/ttyACM0")
)
tools.pipette = Pipette(arduino=tools.arduino)
panda_lib.actions.transfer(
    100,
    "S1",
    "A1",
    toolkit=tools,
)
