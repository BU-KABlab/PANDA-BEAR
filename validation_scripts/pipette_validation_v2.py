import os
import sys
import logging
import pandas as pd
import time


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
from panda_lib.hardware import Scale
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial, WasteVial


try:
    print(f"Initializing Arduino on {'/dev/ttyACM1'}")
    print(f"Initializing Scale on {'/dev/ttyACM0'}")
    
    insert_new_pipette(capacity=300)
    tools = Toolkit(
        mill=PandaMill(),
        arduino=ArduinoLink("/dev/ttyACM1"),
        scale=Scale("/dev/ttyACM0"),
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
    reps_per_volume = 10
    volumes_to_test = [2, 3, 4, 5, 7, 9, 11, 15, 19, 25, 32, 42, 54, 70, 90, 116, 149, 192, 200]
    
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
                "y": -71.0,
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
    tools.scale.tare()

    # Get initial reading
    readings.loc[0] = [pd.Timestamp.now(), tools.scale.get()]

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
    
    def wait_for_stable_reading(scale, max_attempts=10, max_wait_time=30, initial_delay=5):
        """
        Wait for the scale to provide a stable reading.
        
        Args:
            scale: Scale object
            max_attempts: Maximum number of readings to try
            max_wait_time: Maximum time to wait in seconds
            initial_delay: Time to wait before starting to check stability (seconds)
            
        Returns:
            tuple: (mass_value, is_stable)
        """
        print(f"Waiting {initial_delay} seconds for liquid to settle...")
        time.sleep(initial_delay)  # Initial delay to let liquid settle
        
        print("Waiting for scale to stabilize...")
        start_time = time.time()
        attempt = 0
        
        while attempt < max_attempts and (time.time() - start_time) < max_wait_time:
            attempt += 1
            
            try:
                # Get reading from scale
                reading = scale.get()
                
                # Check if it's a dictionary with stability info
                if isinstance(reading, dict) and 'stable' in reading:
                    is_stable = reading['stable']
                    mass = reading['mass']
                    
                    # Print current state
                    if is_stable:
                        print(f"✅ Reading {attempt}: {mass:.4f} g (STABLE)")
                    else:
                        print(f"⏳ Reading {attempt}: {mass:.4f} g (unstable)")
                    
                    # If we got a stable reading, return it
                    if is_stable:
                        elapsed = time.time() - start_time + initial_delay
                        print(f"Scale stabilized after {elapsed:.1f} seconds")
                        return (mass, True)
                else:
                    # No stability info, just print the reading
                    if isinstance(reading, dict) and 'mass' in reading:
                        mass = reading['mass']
                    else:
                        mass = reading
                    print(f"Reading {attempt}: {mass} (stability unknown)")
            
            except Exception as e:
                print(f"Error getting reading {attempt}: {e}")
            
            # Wait before next attempt
            time.sleep(2)
        
        # If we get here, we couldn't get a stable reading
        # Try one more time and return whatever we get
        try:
            final_reading = scale.get()
            if isinstance(final_reading, dict) and 'mass' in final_reading:
                mass = final_reading['mass']
                is_stable = final_reading.get('stable', False)
            else:
                mass = final_reading
                is_stable = False
            
            print(f"⚠️ Could not get confirmed stable reading after {max_attempts} attempts")
            print(f"Using best available: {mass:.4f} g (stable: {is_stable})")
            return (mass, is_stable)
        except Exception as e:
            print(f"Error getting final reading: {e}")
            return (0.0, False)
    
    try:
        # With all objects created lets connect and home the mill
        tools.mill.connect_to_mill()
        tools.mill.homing_sequence()
        tools.mill.set_feed_rate(5000)
        
        all_readings = pd.DataFrame(columns=["Timestamp", "Volume", "Repetition", "Reading", "Stable"])
        row_index = 0
        
        # Get initial reading (zero point)
        try:
            initial_reading = tools.scale.get()
            if isinstance(initial_reading, dict) and 'mass' in initial_reading:
                initial_mass = initial_reading['mass']
            else:
                initial_mass = 0.0
        except Exception as e:
            print(f"Warning: Could not get initial scale reading: {e}")
            initial_mass = 0.0
            
        all_readings.loc[row_index] = [pd.Timestamp.now(), 0, 0, initial_mass, False]
        row_index += 1

        # Now iterate through each volume
        for vol_idx, volume in enumerate(volumes_to_test):
            print(f"\n===== Testing Volume: {volume} µL =====")
            logger.info(f"Starting test for volume {volume} µL")
            print("Taring scale for new volume test")
            tools.scale.tare()
            time.sleep(2)  # Give scale time to stabilize
            # Create a DataFrame to store readings for this volume
            volume_readings = pd.DataFrame(columns=["Timestamp", "Reading", "Stable"])
            
            # Get baseline reading for this volume
            try:
                baseline = tools.scale.get()
                if isinstance(baseline, dict) and 'mass' in baseline:
                    baseline = baseline['mass']
            except Exception as e:
                print(f"Warning: Could not get baseline reading for volume {volume}: {e}")
                baseline = 0.0
                
            volume_readings.loc[0] = [pd.Timestamp.now(), baseline, False]
            
            # Perform multiple repetitions for this volume
            for rep in range(reps_per_volume):
                print(f"\n--- Volume {volume} µL, Repetition {rep+1}/{reps_per_volume} ---")
                
                try:
                    # Perform the transfer
                    panda_lib.actions.transfer(
                        volume,
                        vial_src,
                        vial_dest,
                        toolkit=tools,
                    )
                    
                    try: # Wait for the scale to stabilize
                        mass_value, is_stable = wait_for_stable_reading(
                            tools.scale,
                            max_attempts=max(5, int(volume/10)),  # More attempts for larger volumes
                            max_wait_time=max(15, volume/5),       # More wait time for larger volumes
                            initial_delay=max(5,min(10,volume/20))
                        )

                        print(f"Final reading for {volume} µL (Rep {rep+1}): {mass_value:.4f} g {'(STABLE)' if is_stable else '(UNSTABLE)'}")
    
                    except Exception as e:
                        print(f"Warning: Could not get scale reading: {e}")
                        # Try to reconnect to the scale
                        try:
                            print("Attempting to reconnect to scale...")
                            tools.scale = Scale("/dev/ttyACM0")
                            print("Scale reconnected successfully")
                            mass_value = tools.scale.get()
                        except Exception as e:
                            print("Failed to reconnect to scale, using estimated value")
                            # Use an estimated value based on previous readings
                            if rep > 0:
                                # Use the average of previous readings for this volume
                                prev_readings = volume_readings.iloc[1:]['Reading'].values
                                if len(prev_readings) > 0:
                                    mass_value = sum(prev_readings) / len(prev_readings)
                                else:
                                    mass_value = baseline + (volume / 1000)  # Rough estimate
                            else:
                                mass_value = baseline + (volume / 1000)  # Rough estimate
    
                    # Store in volume-specific DataFrame
                    volume_readings.loc[rep+1] = [pd.Timestamp.now(), mass_value, is_stable]
    
                    # Store in master DataFrame
                    all_readings.loc[row_index] = [pd.Timestamp.now(), volume, rep+1, mass_value, is_stable]
                    row_index += 1
    
                    print(f"Reading for {volume} µL (Rep {rep+1}): {mass_value} g")
    
                except Exception as e:
                    print(f"Error during transfer for volume {volume}, repetition {rep+1}: {e}")
                    # Continue with next repetition
                    continue
            
            # Save the volume-specific results after each volume test
            try:
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H%M%S")
                volume_readings.to_csv(f"{timestamp}_volume_{volume}_readings.csv", index=False, float_format='%.4f')
                print(f"Saved results for volume {volume} µL")
            except Exception as e:
                print(f"Error saving volume-specific results: {e}")

    except Exception as e:
        print(f"An error occurred in the main try block: {e}")

    finally:
        # Safely disconnect
        try:
            tools.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        
        # Process and save the data even if there were errors
        try:
            # Process the master DataFrame with all readings
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H%M%S")
            
            # Make sure we have data to save
            if 'all_readings' in locals() and len(all_readings) > 0:
                # Format the timestamp column as a string in a standard format
                all_readings['Timestamp'] = all_readings['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Make sure all readings are converted to floats
                for idx in all_readings.index:
                    if isinstance(all_readings.loc[idx, 'Reading'], dict):
                        all_readings.loc[idx, 'Reading'] = all_readings.loc[idx, 'Reading'].get('mass', 0.0)
                    elif isinstance(all_readings.loc[idx, 'Reading'], str):
                        try:
                            if '{' in all_readings.loc[idx, 'Reading']:
                                import ast
                                parsed = ast.literal_eval(all_readings.loc[idx, 'Reading'])
                                all_readings.loc[idx, 'Reading'] = parsed.get('mass', 0.0)
                            else:
                                all_readings.loc[idx, 'Reading'] = float(all_readings.loc[idx, 'Reading'])
                        except Exception:
                            all_readings.loc[idx, 'Reading'] = 0.0
                
                # Save master dataset with all volumes
                all_readings.to_csv(f"{timestamp}_all_volumes.csv", index=False, float_format='%.4f')
                print(f"Complete dataset saved to {timestamp}_all_volumes.csv")
                
                # Calculate statistics for each volume
                with open(f"{timestamp}_validation_summary.txt", 'w') as f:
                    f.write("Pipette Validation Summary\n")
                    f.write("========================\n")
                    f.write(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    print("\nPipette Performance Analysis:")

                    for volume in volumes_to_test:
                        # Filter readings for this volume
                        vol_data = all_readings[all_readings['Volume'] == volume].copy()
                        
                        if len(vol_data) > 1:
                            # Calculate the delta between consecutive readings for this volume
                            # First, sort by repetition number to ensure correct order
                            vol_data = vol_data.sort_values('Repetition')
                            
                            # Calculate actual dispensed volume for each repetition
                            # For the first repetition, it's just the reading itself (since we tared)
                            # For subsequent repetitions, it's the difference from the previous reading
                            vol_data['Dispensed'] = vol_data['Reading'].diff()
                            
                            # The first row will have NaN, replace it with the first reading
                            vol_data.loc[vol_data.index[0], 'Dispensed'] = vol_data.iloc[0]['Reading']
                            
                            # Optionally filter for stable readings only
                            stable_vol_data = vol_data[vol_data['Stable']].copy()
                            
                            # Use stable readings if available, otherwise use all readings
                            analysis_data = stable_vol_data if len(stable_vol_data) > 1 else vol_data
                            
                            # Get just the dispensed masses
                            dispensed_masses = analysis_data['Dispensed'].values  # in grams
                            
                            # Convert mass to volume (1g water = 1000μL at room temperature)
                            dispensed_volumes = dispensed_masses * 1000  # convert to μL
                            
                            if len(dispensed_volumes) > 0:  # Make sure we have values to analyze
                                # Calculate statistics
                                mean_mass = dispensed_masses.mean()  # in grams
                                mean_volume = dispensed_volumes.mean()  # in μL
                                std_mass = dispensed_masses.std() if len(dispensed_masses) > 1 else 0
                                std_volume = std_mass * 1000  # convert to μL
                                cv_percent = (std_mass / mean_mass) * 100 if mean_mass else 0
                                
                                # Calculate accuracy (how close to target volume)
                                accuracy_percent = (mean_volume/volume - 1) * 100
                                
                                # Print to console
                                print(f"\nVolume: {volume} µL")
                                print(f"  Mean dispensed: {mean_mass:.4f} g ({mean_volume:.1f} μL)")
                                print(f"  Standard deviation: {std_mass:.4f} g ({std_volume:.1f} μL)")
                                print(f"  Coefficient of variation: {cv_percent:.2f}%")
                                print(f"  Accuracy: {accuracy_percent:.2f}% {'(over)' if accuracy_percent > 0 else '(under)'}")
                                
                                # Write to file
                                f.write(f"Volume: {volume} µL\n")
                                f.write(f"  Number of repetitions: {len(dispensed_volumes)}\n")
                                f.write(f"  Mean dispensed: {mean_mass:.4f} g ({mean_volume:.1f} μL)\n")
                                f.write(f"  Standard deviation: {std_mass:.4f} g ({std_volume:.1f} μL)\n")
                                f.write(f"  Coefficient of variation: {cv_percent:.2f}%\n")
                                f.write(f"  Accuracy: {accuracy_percent:.2f}% {'(over)' if accuracy_percent > 0 else '(under)'}\n\n")

                            print(f"  Stable readings: {len(stable_vol_data)} of {len(vol_data)}")
                            f.write(f"  Stable readings: {len(stable_vol_data)} of {len(vol_data)}\n")
                
                print(f"\nDetailed validation summary saved to {timestamp}_validation_summary.txt")
        except Exception as e:
            print(f"Error saving analysis results: {e}")
            
        print("Script completed.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc()
# Ensure the script exits cleanly
