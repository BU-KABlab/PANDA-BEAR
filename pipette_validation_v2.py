import panda_lib
from panda_lib.hardware import ArduinoLink, PandaMill, Scale
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit
import asyncio
from panda_lib.types import VialKwargs, WellKwargs
from panda_lib.labware.vials import StockVial
from panda_lib.labware.wellplates import Well
import logging

logger = logging.getLogger("panda")
async def tare_scale():
    await tools.scale.zero()
    print("Scale zeroed")

async def read_scale():
    # await tools.scale.zero()
    reading = await tools.scale.get()
    print(reading)
insert_new_pipette(capacity=300)
tools = Toolkit(
    mill=PandaMill(), # NOTE: The mill needs to be connected and homed before use
    arduino=ArduinoLink("/dev/ttyACM1"),
    scale=Scale("/dev/ttyACM0"),
    global_logger=logger,

)
tools.pipette = Pipette(arduino=tools.arduino)

vkwargs = VialKwargs(
            category=0,
            name="IPA",
            contents={"IPA": 20000},
            viscosity_cp=1,
            concentration=0.01,
            density=1,
            height=66,
            radius=14,
            volume=20000,
            capacity=20000,
            contamination=0,
            coordinates={
                "x": -67.5,
                "y": -44.0,
                "z": -197,
            },  # TODO replace with vial coordinates
            base_thickness=1,
            dead_volume=1000,
        )
vial = StockVial(
    position="s10", create_new=True, **vkwargs
)
vial.save()

wellKwargs = WellKwargs(
    name="B1",
    volume=0,
    height=10,
    radius=5,
    contamination=0,
    dead_volume=100,
    contents={},
    coordinates={
        "x": -100,
        "y": -100,
        "z": -197,
    },  # TODO replace with vial coordinates
    type_id=7
    
)
well = Well(
    well_id="B1", plate_id=115,create_new=True, **wellKwargs
)
well.save()

asyncio.run(read_scale())

# With all objects created lets connect and home the mill
try:
    tools.mill.connect_to_mill()
    tools.mill.homing_sequence()

    panda_lib.actions.transfer(
        100,
        vial,
        well,
        toolkit=tools,
    )


finally:
    tools.disconnect()