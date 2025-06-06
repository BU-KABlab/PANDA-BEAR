import os
import sys
import logging
import pandas as pd

# Set up logging first
logger = logging.getLogger("panda")
logger.setLevel(logging.DEBUG)

# IMPORTANT: We need to patch both places where decapping might be imported from
# First patch movement.py directly
from panda_lib.actions import movement

# Also patch the pipetting module since it imports these functions
import panda_lib.actions.pipetting

# Create replacement functions
def no_op_decap(*args, **kwargs):
    logger.info("SKIPPED: Decapping operation (disabled by monkey patch)")
    return None

def no_op_cap(*args, **kwargs):
    logger.info("SKIPPED: Capping operation (disabled by monkey patch)")
    return None

# Apply patches to both modules
movement.decapping_sequence = no_op_decap
movement.capping_sequence = no_op_cap

# This is the key fix - we need to patch pipetting's reference too
# It may have imported the original functions at import time
if hasattr(panda_lib.actions.pipetting, "decapping_sequence"):
    panda_lib.actions.pipetting.decapping_sequence = no_op_decap
if hasattr(panda_lib.actions.pipetting, "capping_sequence"):
    panda_lib.actions.pipetting.capping_sequence = no_op_cap

logger.info("Successfully applied monkey patch to disable decapping/capping")

# Test the patched functions
print("Testing patched functions:")
movement.decapping_sequence(None, None, None)  # Should print the "SKIPPED" message
movement.capping_sequence(None, None, None)    # Should print the "SKIPPED" message

# Continue with your imports
from panda_lib.hardware import ArduinoLink, PandaMill
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial, WasteVial


# Set up logging
logger = logging.getLogger("panda")
logger.setLevel(logging.DEBUG)  # Increase verbosity

# Check which serial devices are available
print("Checking available serial devices:")
os.system("ls -l /dev/tty*")

# Try to determine the correct ports
arduino_port = "/dev/ttyACM1"
#scale_port = None

'''
# Check for Arduino (ACM devices)
for i in range(5):  # Check ttyACM0 through ttyACM4
    port = f"/dev/ttyACM{i}"
    if os.path.exists(port):
        print(f"Found potential Arduino port: {port}")
        arduino_port = port
        break
'''
# Check for Scale (USB devices from CH340)
'''
for i in range(5):  # Check ttyUSB0 through ttyUSB4
    port = f"/dev/ttyUSB{i}"
    if os.path.exists(port):
        print(f"Found potential Scale port: {port}")
        scale_port = port
        break
'''
# If we didn't find the ports, try some defaults
if not arduino_port:
    arduino_port = "/dev/ttyACM0"  # Default
    print(f"Using default Arduino port: {arduino_port}")
'''
if not scale_port:
    scale_port = "/dev/ttyUSB0"  # Default for CH340
    print(f"Using default Scale port: {scale_port}")
'''
# Initialize with try/except for better error handling
try:
    print(f"Initializing Arduino on {arduino_port}")
#    print(f"Initializing Scale on {scale_port}")
    
    insert_new_pipette(capacity=300)
    tools = Toolkit(
        mill=PandaMill(),
        arduino=ArduinoLink(arduino_port),
        #scale=Scale(scale_port),
        global_logger=logger,
    )
    
    print("Successfully initialized toolkit")
    
    try:
        tools.pipette = Pipette(arduino=tools.arduino)
        print("Successfully initialized pipette")
    except Exception as e:
        print(f"Error initializing pipette: {e}")
        print("Continuing without pipette functionality")
    
    # Number of iterations to run
    n = 1  # Set a default value, update as needed

    readings = pd.DataFrame(columns=["Timestamp","Reading"])
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
                "x": -22.0,
                "y": -74.0,
                "z": -195.0,
            },  # TODO verify vial coordinates
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
        volume=0,
        capacity=20000,
        contamination=0,
        coordinates={
            "x": -252.0,
            "y": -66.0,
            "z": -195.0,
        },  # TODO verify scale coordinates
        base_thickness=1,
        dead_volume=1000,
    )

    vial_dest = WasteVial(
        position="w1", create_new=True, **vial_kwargs_dest
    )
    vial_dest.save()
    # tare the scale
    #tools.scale.tare()

    # Get initial reading
    #readings.loc[0] = [pd.Timestamp.now(), tools.scale.get()]
# ...imports and setup...

    # Define our own transfer function that doesn't use decapping
    from panda_lib.actions.pipetting import _pipette_action as original_pipette_action

    # Create a wrapper that disables decapping
    def _pipette_action_no_decap(*args, **kwargs):
        """Wrapper for _pipette_action that disables decapping"""
        # Before calling the original, patch the functions it calls
        from panda_lib.actions import movement
        
        # Store original functions
        original_decap = movement.decapping_sequence
        original_cap = movement.capping_sequence
        
        # Replace with no-ops
        movement.decapping_sequence = lambda *a, **k: logger.info("SKIPPED: Decapping")
        movement.capping_sequence = lambda *a, **k: logger.info("SKIPPED: Capping")
        
        try:
            # Call the original with decapping disabled
            result = original_pipette_action(*args, **kwargs)
            return result
        finally:
            # Restore original functions
            movement.decapping_sequence = original_decap
            movement.capping_sequence = original_cap

    # Patch the pipette action function
    panda_lib.actions.pipetting._pipette_action = _pipette_action_no_decap

    # Also patch the transfer function to use our version
    import panda_lib.actions
    original_transfer = panda_lib.actions.transfer

    def transfer_no_decap(*args, **kwargs):
        """Wrapper for transfer that uses our patched _pipette_action"""
        logger.info("Using transfer function with decapping disabled")
        return original_transfer(*args, **kwargs)

    # Apply the patch
    panda_lib.actions.transfer = transfer_no_decap
    
    try:
        # With all objects created lets connect and home the mill
        tools.mill.connect_to_mill()
        tools.mill.homing_sequence()
        tools.mill.set_feed_rate(2000) # TODO set back to 5000 for real test

        # Now lets iterate over the number of times we want to transfer
        # the vial contents and read the scale
        for i in range(n):
            panda_lib.actions.transfer(
                100,
                vial_src,
                vial_dest,
                toolkit=tools,
            )
            
            #readings.loc[i+1] = [pd.Timestamp.now(), tools.scale.get()]
            
    finally:
        tools.disconnect()

        # Save the readings to a CSV file
        #timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        #readings.to_csv(f"{timestamp}_scale_readings.csv", index=False)
        #print(f"Scale readings saved to {timestamp}_scale_readings.csv")
        print("Disconnected from all devices successfully.")
except Exception as e:
    print(f"An error occurred in the main try block: {e}")
    # Optional: add some cleanup code here if needed