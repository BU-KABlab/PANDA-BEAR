"""
Contact Angle Validation Script
This script performs a contact angle validation test by dispensing droplets 
on a glass slide, capturing images, and then aspirating the droplets.
"""
import sys
import os
from pathlib import Path
import cv2
import numpy as np
from panda_lib.hardware.imaging import capture_new_image, CameraType
from datetime import datetime
import logging
import pandas as pd
import time

# Set up logging
logger = logging.getLogger("panda")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
file_handler = logging.FileHandler("contactangle_validation.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Import PANDA libraries
from panda_lib.hardware import ArduinoLink, PandaMill
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial, WasteVial

# Disable decapping/capping operations
from panda_lib.actions import movement
import panda_lib.actions.pipetting


# Create replacement functions for skipping capping/decapping
def no_op_decap(*args, **kwargs):
    logger.info("SKIPPED: Decapping operation (disabled by monkey patch)")
    return None

def no_op_cap(*args, **kwargs):
    logger.info("SKIPPED: Capping operation (disabled by monkey patch)")
    return None

# Apply patches to both modules
movement.decapping_sequence = no_op_decap
movement.capping_sequence = no_op_cap
panda_lib.actions.pipetting.decapping_sequence = no_op_decap
panda_lib.actions.pipetting.capping_sequence = no_op_cap
logger.info("Successfully applied monkey patch to disable decapping/capping")

class SlidePosition:
    def __init__(self, name: str, x: float, y: float, z: float):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.volume = 0
        self.contents = {}
        self.top = z + 2
        self.bottom = z
        self.withdrawal_height = z + 0.5
        self.aspirate_height = z + 0.5

    def __repr__(self):
        return f"SlidePosition(name={self.name}, x={self.x}, y={self.y}, z={self.z})"


try:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Create directory for this experiment's images
    experiment_dir = f"contact_angle_experiment_{timestamp}"
    os.makedirs(experiment_dir, exist_ok=True)
    logger.info(f"Created experiment directory: {experiment_dir}")
    
    # Set up the hardware
    logger.info("Initializing hardware components...")
    from panda_lib.hardware.imaging.camera_factory import CameraFactory
    insert_new_pipette(capacity=300)
    tools = Toolkit(
        mill=PandaMill(),
        arduino=ArduinoLink("/dev/ttyACM0"),
        camera=CameraFactory.create_camera(camera_type=CameraType.FLIR),
        global_logger=logger,
    )

    if tools.camera:
        logger.info("Connecting to FLIR camera...")
        if tools.camera.connect():
            logger.info("FLIR camera connected successfully")
        else:
            logger.error("Failed to connect to FLIR camera")
            raise RuntimeError("Could not connect to FLIR camera")
    else:
        logger.error("FLIR camera not created")
        raise RuntimeError("FLIR camera not available")

    
    print("Successfully initialized toolkit")
    
    # Initialize pipette
    tools.pipette = Pipette(arduino=tools.arduino)
    print("Successfully initialized pipette")
    # Create a fixed test volume
    test_volume = 10  # 10 µL for contact angle testing
    
    # Define slide positions using mill coordinates
    slide_positions = [
        SlidePosition("A", -192.8, -90.3, -191.5),
        SlidePosition("B", -202.8, -90.3, -191.5),
        SlidePosition("C", -202.8, -80.3, -191.5),
        SlidePosition("D", -192.8, -80.3, -191.5),
    ]

    
    # Set up source vial (stock solution)
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
            "x": -21.8,
            "y": -43.3,
            "z": -197.0,
        },
        base_thickness=1,
        dead_volume=1000,
    )
    vial_src = StockVial(
        position="s1", create_new=True, **vkwargs_src
    )
    vial_src.save()
    
    # Set up waste vial
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
            "x": -21.8,
            "y": -76.3,
            "z": -197.0,
        },
        base_thickness=1,
        dead_volume=1000,
    )
    vial_dest = WasteVial(
        position="w1", create_new=True, **vial_kwargs_dest
    )
    vial_dest.save()
    
    # Home the mill
    logger.info("Connecting to mill and homing...")
    tools.mill.connect_to_mill()
    if not tools.mill.ser_mill:
        raise RuntimeError("Failed to connect to the mill.")
    tools.mill.homing_sequence()
    tools.mill.set_feed_rate(5000)
    
    # Create a results dataframe
    results = pd.DataFrame(columns=["Timestamp", "Slide_Number", "Position", "Image_Path"])
    row_index = 0
    
    def rank_images_by_sharpness(image_paths):
        """
        Rank a list of image paths based on Laplacian sharpness.
        
        Args:
            image_paths (list of str or Path): Paths to images to compare.
            
        Returns:
            List of tuples: [(image_path, sharpness_score), ...] sorted by score descending
        """
        ranked = []

        for path in image_paths:
            try:
                img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    logger.warning(f"Could not load image: {path}")
                    continue
                laplacian = cv2.Laplacian(img, cv2.CV_64F)
                variance = laplacian.var()
                ranked.append((path, variance))
                logger.info(f"Sharpness score for {path}: {variance:.2f}")
            except Exception as e:
                logger.error(f"Error analyzing image {path}: {e}", exc_info=True)

        ranked.sort(key=lambda x: x[1], reverse=True)  # Descending sharpness
        return ranked

    # Function to capture an image of the droplet
    def capture_droplet_image(slide_num, position_idx):
        """Capture images of the droplet at different Z heights using FLIR camera."""
        position = slide_positions[position_idx]
        base_file_name = f"slide{slide_num}_pos{position.name}"
        camera_x = position.x
        camera_y = position.y
        # Turn on lights
        logger.info("Turning on contact angle lights")
        tools.arduino.curvature_lights_on()
        time.sleep(1)  # Let lighting stabilize
        # Try these Z heights
        z_heights = [-38.0, -38.2, -38.5, -38.7, -39.0, -39.2,-39.5, -39.7, -40.0, -40.2, -40.5, -40.7, -41.0, -41.2, -41.5]
        captured_paths = []

        for z in z_heights:
            image_path = Path(experiment_dir) / f"{base_file_name}_z{z:.1f}.tiff"
            logger.info(f"Moving to position for imaging: ({camera_x}, {camera_y}, {z})")
            tools.mill.safe_move(camera_x, camera_y, z, tool="lens")
            time.sleep(1)  # Let vibration settle

            # Capture image
            logger.info(f"Capturing image with FLIR camera at Z={z}")
            try:
                actual_path, success = capture_new_image(
                    save=True,
                    file_name=image_path,
                    camera_type=CameraType.FLIR
                )
                if success:
                    logger.info(f"Captured image to {image_path}")
                    captured_paths.append(str(image_path))
                else:
                    logger.error(f"Failed to capture image at Z={z}")
            except Exception as e:
                logger.error(f"Error capturing at Z={z}: {e}", exc_info=True)


        logger.info("Turning off contact angle lights")
        tools.arduino.curvature_lights_off()       
        return captured_paths  # Return all image paths for review
        
    
    # Function to prompt user for slide replacement
    def prompt_for_slide_replacement():
        """Ask user if they want to replace the slide or end the experiment."""
        while True:
            response = input("\nDo you want to:\n"
                            "1. Replace the slide and continue\n"
                            "2. End the experiment\n"
                            "Enter 1 or 2: ")
            if response == "1":
                input("Replace the slide, then press Enter to continue...")
                return True
            elif response == "2":
                return False
            else:
                print("Invalid response. Please enter 1 or 2.")
    
    # Main experiment loop
    slide_number = 1
    continue_experiment = True
    
    while continue_experiment:
        print(f"\n===== Testing Slide #{slide_number} =====")
        logger.info(f"Starting tests on slide #{slide_number}")
        
        # For each position on the slide
        for pos_idx, position in enumerate(slide_positions):
            print(f"\n--- Testing Position {position.name} ---")
            logger.info(f"Testing slide {slide_number}, Position {position.name}")
            
            try:
                # Step 1: Dispense droplet
                print(f"Dispensing {test_volume} µL onto slide position {position.name}...")
                logger.info(f"Dispensing {test_volume} µL at Position {position.name}")
                panda_lib.actions.transfer(
                    test_volume,
                    vial_src,
                    position,
                    toolkit=tools,
                )
                position.contents = {"H2O": test_volume}
               
                # Step 2: Capture image of the droplet
                print("Capturing image of the droplet...")
                image_paths = capture_droplet_image(slide_number, pos_idx)
                ranked = rank_images_by_sharpness(image_paths)

                # Log the sharpest image
                if ranked:
                    best_image_path = ranked[0][0]
                    results.loc[row_index] = [
                        datetime.now().strftime("%Y-%m-%d_%H%M%S"),
                        slide_number,
                        position.name,
                        str(best_image_path)
                    ]
                    row_index += 1

                    print("\nTop sharpest image:")
                    print(f"{best_image_path} (Score: {ranked[0][1]:.2f})")


                # Add pause with prompt after image is captured and lights are off
                user_input = input(f"\nImage captured for slide {slide_number}, position {position.name}. Press Enter to aspirate the droplet and continue, or type 'skip' to leave the droplet: ")
                
                if user_input.lower() == 'skip':
                    logger.info(f"User chose to skip aspiration for slide {slide_number}, position {position.name}")
                    print(f"Skipping aspiration for position {position.name}")
                    continue

                # Step 3: Aspirate the droplet and move it to waste
                print("Aspirating droplet to waste...")
                logger.info(f"Removing droplet from Position {position.name}")
                panda_lib.actions.transfer(
                    test_volume,
                    position,
                    vial_dest,
                    toolkit=tools,
                )
                
                print(f"Completed test on slide {slide_number}, Position {position.name}")
                
            except Exception as e:
                print(f"Error during contact angle test at Position {position.name}: {e}")
                logger.error(f"Error at Position {position.name}: {e}", exc_info=True)
                # Continue with next position
        
        # After all positions on this slide are complete
        print(f"\nCompleted all positions on slide #{slide_number}")
        logger.info(f"Completed all tests on slide #{slide_number}")
        
        # Periodically save results
        temp_results_file = f"{experiment_dir}/contact_angle_results_partial.csv"
        results.to_csv(temp_results_file, index=False)
        logger.info(f"Saved partial results to {temp_results_file}")
        
        # Step 5: Prompt user for slide replacement or experiment end
        continue_experiment = prompt_for_slide_replacement()
        if continue_experiment:
            slide_number += 1
    
    # Save final results to CSV
    results_file = f"{experiment_dir}/contact_angle_results.csv"
    if not results.empty:
        results.to_csv(results_file, index=False)
    print(f"\nResults saved to {results_file}")
    logger.info(f"Final results saved to {results_file}")
    
    # Create summary report
    summary_file = f"{experiment_dir}/experiment_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("Contact Angle Validation Summary\n")
        f.write("==============================\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d_%H%M%S')}\n")
        f.write(f"Total slides tested: {slide_number}\n")
        f.write(f"Positions per slide: {len(slide_positions)}\n")
        f.write(f"Droplet volume: {test_volume} µL\n\n")
        f.write(f"Images captured: {len(results)}\n")
        f.write("Images are stored in the experiment directory for further analysis.\n")
    
    print(f"Experiment summary saved to {summary_file}")
    logger.info("Experiment completed successfully")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
    logger.error(f"Experiment failed: {e}", exc_info=True)

finally:
    # Cleanup
    try:
        if 'tools' in locals():
            # Make sure lights are off FIRST before closing Arduino
            if hasattr(tools, 'arduino'):
                try:
                    logger.info("Ensuring all lights are off")
                    tools.arduino.curvature_lights_off()
                    tools.arduino.white_lights_off()
                except Exception as e:
                    logger.warning(f"Error while turning off lights during cleanup: {e}")
            # Disconnect mill
            try:
                if tools.mill:
                    tools.mill.disconnect()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

            # Close Arduino connection LAST (after using it to turn off lights)
            if hasattr(tools, 'arduino'):
                tools.arduino.close()
                logger.info("Arduino closed")

            try:
                if hasattr(tools, "camera") and tools.camera:
                    logger.info("Disconnecting FLIR camera")
                    tools.camera.close()
                    tools.camera = None  # Ensure reference is dropped
            except Exception as e:
                logger.warning(f"Error while disconnecting camera: {e}")

        print("Hardware disconnected. Script completed.")
        logger.info("Cleanup completed")
    except Exception as cleanup_error:
        print(f"Error during cleanup: {cleanup_error}")
        logger.error(f"Cleanup error: {cleanup_error}", exc_info=True)
