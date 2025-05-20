import panda_lib
from panda_lib.hardware import ArduinoLink, PandaMill
from panda_lib.hardware import Scale
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial, WasteVial
import logging
import pandas as pd

logger = logging.getLogger("panda")

insert_new_pipette(capacity=300)
tools = Toolkit(
    mill=PandaMill(),  # NOTE: The mill needs to be connected and homed before use
    arduino=ArduinoLink("/dev/ttyACM1"),
    scale=Scale("/dev/ttyACM0"),
    global_logger=logger,
)
tools.pipette = Pipette(arduino=tools.arduino)

# Number of iterations to run
n = 5  # Set a default value, update as needed

readings = pd.DataFrame(columns=["Timestamp", "Reading"])
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
        "x": -93.0,
        "y": -225.0,
        "z": -197.0,
    },  # TODO replace with vial coordinates
    base_thickness=1,
    dead_volume=1000,
)
vial_src = StockVial(position="s1", create_new=True, **vkwargs_src)
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
        "x": -268.0,
        "y": -284.0,
        "z": -195.0,  # NOTE this is higher since its in the new vial holder
    },  # TODO replace with vial coordinates
    base_thickness=1,
    dead_volume=1000,
)

vial_dest = WasteVial(position="w1", create_new=True, **vial_kwargs_dest)
vial_dest.save()
# tare the scale
tools.scale.tare()

# Get initial reading
readings.loc[0] = [pd.Timestamp.now(), tools.scale.get()]


try:
    # With all objects created lets connect and home the mill
    tools.mill.connect_to_mill()
    tools.mill.homing_sequence()
    tools.mill.set_feed_rate(2000)  # TODO set back to 5000 for real test

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
        readings.loc[i + 1] = [pd.Timestamp.now(), tools.scale.get()]
        # TODO Transfer the vial back to the holder

finally:
    tools.disconnect()

    # Save the readings to a CSV file
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    readings.to_csv(f"{timestamp}_scale_readings.csv", index=False)
    print(f"Scale readings saved to {timestamp}_scale_readings.csv")
