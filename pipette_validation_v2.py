import panda_lib
from panda_lib.hardware import ArduinoLink, PandaMill, Scale
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit
import asyncio
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial, WasteVial
import logging
import pandas as pd
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
tools.mill.set_feed_rate(2000) # TODO set back to 5000 for real test
readings = pd.DataFrame(columns=["Timestamp","Reading"])
n = 1 # TODO update with the number of itterations
vkwargs_src = VialKwargs(
            category=0,
            name="H20",
            contents={"H20": 20000},
            viscosity_cp=1,
            concentration=0.01,
            density=1,
            height=66,
            radius=14,
            volume=20000,
            capacity=20000,
            contamination=0,
            coordinates={
                "x": -167.0,
                "y": -291.0,
                "z": -195.0,
            },  # TODO replace with vial coordinates
            base_thickness=1,
            dead_volume=1000,
        )
vial_src = StockVial(
    position="s1", create_new=True, **vkwargs_src
)
vial_src.save()

vial_kwargs_dest = VialKwargs(
    category=1,
    name="waste",
    contents={"H20": 0},
    viscosity_cp=1,
    concentration=0.01,
    density=1,
    height=66,
    radius=14,
    volume=20000,
    capacity=20000,
    contamination=0,
    coordinates={
        "x": -393.0,
        "y": -247.0,
        "z": -195.0,
    },  # TODO replace with vial coordinates
    base_thickness=1,
    dead_volume=1000,
)

vial_dest = WasteVial(
    position="w1", create_new=True, **vial_kwargs_dest
)
vial_dest.save()
# tare the scale
asyncio.run(tare_scale())

readings.loc[0] = [pd.Timestamp.now(), asyncio.run(read_scale())]


try:
    # With all objects created lets connect and home the mill
    tools.mill.connect_to_mill()
    tools.mill.homing_sequence()

    # Now lets iterate over the number of times we want to transfer
    # the vial contents and read the scale
    for i in range(n):
        panda_lib.actions.transfer(
            100,
            vial_src,
            vial_dest,
            toolkit=tools,
        )
        # TODO Transfer the vial to the scale
        readings.loc[i+1] = [pd.Timestamp.now(), asyncio.run(read_scale())]
        # TODO Transfer the vial back to the holder

finally:
    tools.disconnect()

    # Save the readings to a CSV file
    df = pd.DataFrame(readings, columns=["Reading"])
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(f"{timestamp}_scale_readings.csv", index=False)
    print("Scale readings saved to scale_readings.csv")