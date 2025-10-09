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

# Replace with direct function imports:
from panda_lib.actions.movement import decapping_sequence, capping_sequence
import panda_lib.actions.pipetting as pipetting_module
from panda_lib.actions.pipetting import transfer

# Create replacement functions for skipping capping/decapping
def no_op_decap(*args, **kwargs):
    logger.info("SKIPPED: Decapping operation (disabled by monkey patch)")
    return None

def no_op_cap(*args, **kwargs):
    logger.info("SKIPPED: Capping operation (disabled by monkey patch)")
    return None

# Apply patches to specific functions (not entire modules)
import panda_lib.actions.movement
import panda_lib.actions.pipetting

panda_lib.actions.movement.decapping_sequence = no_op_decap
panda_lib.actions.movement.capping_sequence = no_op_cap
panda_lib.actions.pipetting.decapping_sequence = no_op_decap
panda_lib.actions.pipetting.capping_sequence = no_op_cap
logger.info("Successfully applied monkey patch to disable decapping/capping")

from panda_lib.hardware.gantry_interface import Coordinates

class SlidePosition:
    def __init__(self, name: str, x: float, y: float, z: float):
        self.name = name
        self.position = name  # Add position property like Well class
        self.volume = 0
        self.contents = {}
        
        # Vessel properties that transfer function expects
        self.capacity = 1000  # Max volume it can hold
        self.dead_volume = 0   # No dead volume for a slide
        self.radius = 5        # Approximate radius for droplet spread
        self.height = 3        # Height above slide surface
        self.base_thickness = 0
        self.viscosity_cp = 1
        self.concentration = 0
        self.density = 1
        self.contamination = 0
        
        # Coordinate properties that match Well class
        self.coordinates = {"x": x, "y": y, "z": z}
        self._x = x
        self._y = y
        self._z = z
        self.top = z + 2
        self.bottom = z
        self.withdrawal_height = z + 0.5
        self.aspirate_height = z + 0.5
        
    # Properties that match Well class interface
    @property
    def x(self):
        return self._x
    
    @property
    def y(self):
        return self._y
    
    @property
    def z(self):
        return self._z
    
    @property
    def top_coordinates(self) -> Coordinates:
        """Returns the top coordinates of the position."""
        return Coordinates(x=self.x, y=self.y, z=self.top)
    
    @property
    def bottom_coordinates(self) -> Coordinates:
        """Returns the bottom coordinates of the position."""
        return Coordinates(x=self.x, y=self.y, z=self.bottom)
    
    @property
    def volume_height(self):
        """The z-coordinate of the predicted volume top in the position"""
        return self.get_liquid_height()
    
    def get_liquid_height(self):
        """Calculate current liquid height based on volume"""
        if self.volume <= 0:
            return self.bottom
        # For a droplet on a slide, height is roughly proportional to volume
        droplet_height = (self.volume / 100) * 0.1  # Very rough approximation
        return self.bottom + droplet_height
    
    def get_aspiration_height(self):
        """Get the height for aspiration - slightly above liquid surface"""
        liquid_height = self.get_liquid_height()
        return liquid_height + 0.1  # 0.1mm above liquid surface
    
    def get_dispensing_height(self):
        """Get the height for dispensing - close to slide surface"""
        return self.bottom + 2.8  # 2.8mm above slide surface

    def get_withdrawal_height(self):
        """Returns the height from which contents are withdrawn."""
        return self.get_aspiration_height()
    
    def add_volume(self, volume_ul):
        """Add volume to the position"""
        self.volume += volume_ul
        # Update contents (assuming water for now)
        if "H2O" not in self.contents:
            self.contents["H2O"] = 0
        self.contents["H2O"] += volume_ul
    
    def remove_volume(self, volume_ul):
        """Remove volume from the position"""
        if self.volume >= volume_ul:
            self.volume -= volume_ul
            if "H2O" in self.contents:
                self.contents["H2O"] = max(0, self.contents["H2O"] - volume_ul)
        else:
            # Can't remove more than what's there
            self.volume = 0
            self.contents = {}
    
    # Methods that match Well class interface
    def add_contents(self, from_vessel: dict, volume: float):
        """Add contents to the position (matches Well.add_contents)"""
        for key, val in from_vessel.items():
            if key in self.contents:
                self.contents[key] += val
            else:
                self.contents[key] = val
        self.volume += volume
    
    def remove_contents(self, volume: float) -> dict:
        """Remove contents from the position (matches Well.remove_contents)"""
        if self.volume == 0:
            return {}
        
        current_content_ratios = {
            key: value / sum(self.contents.values())
            for key, value in self.contents.items()
        }
        removed_contents = {}
        for key in self.contents:
            removed_volume = round(volume * current_content_ratios[key], 6)
            self.contents[key] -= removed_volume
            removed_contents[key] = removed_volume

        self.volume -= volume
        return removed_contents
    
    def save(self):
        """Compatibility method - slides don't need to be saved to database"""
        pass
    
    def __repr__(self):
        return f"SlidePosition(name={self.name}, x={self.x}, y={self.y}, z={self.z}, volume={self.volume})"

try:
    # Pre-import the problematic modules to avoid circular import issues
    import panda_lib.hardware.gamry_potentiostat.gamry_control_mock
    import panda_lib.hardware.emstat_potentiostat.emstat_control_mock
except ImportError:
    pass  # Mock modules might not exist, that's OK

def main():
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
            SlidePosition("A", -217.8, -45.3, -193.5),
            SlidePosition("B", -227.8, -45.3, -193.5),
            SlidePosition("C", -227.8, -35.3, -193.5),
            SlidePosition("D", -217.8, -35.3, -193.5),
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
            z_heights = [-39.0, -39.2,-39.5, -39.7, -40.0, -40.2]
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

                    # Clear any existing volume first
                    position.volume = 0
                    position.contents = {}

                    # Manual dispensing instead of transfer function
                    logger.info("=== PERFORMING MANUAL DISPENSING ===")

                    # Move to source vial position for aspiration
                    src_coords = vial_src.coordinates
                    src_height = vial_src.withdrawal_height  # Use vial's withdrawal height
                    logger.info(f"Moving to source vial position: ({src_coords['x']}, {src_coords['y']}, {src_height})")
                    tools.mill.safe_move(src_coords["x"], src_coords["y"], src_height, tool="pipette")
                    time.sleep(1)

                    # Aspirate from source vial
                    logger.info(f"Aspirating {test_volume} µL from source vial")
                    tools.pipette.aspirate(test_volume)
                    time.sleep(1)

                    # Move to slide dispensing position (3mm above slide surface)
                    dispense_height = position.bottom + 3.0  # 3mm above slide for proper clearance
                    logger.info(f"Moving to slide dispensing position: ({position.x}, {position.y}, {dispense_height})")
                    tools.mill.safe_move(position.x, position.y, dispense_height, tool="pipette")
                    time.sleep(1)

                    # Dispense onto slide
                    logger.info(f"Dispensing {test_volume} µL onto slide position {position.name}")
                    tools.pipette.dispense(test_volume)
                    time.sleep(1)

                    logger.info("Manual dispensing completed successfully")

                    # Update position volume after dispensing
                    position.add_volume(test_volume)
                    logger.info(f"Position {position.name} now contains {position.volume} µL")
                
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
                    logger.info(f"Removing droplet from Position {position.name} (volume: {position.volume} µL)")

                    if position.volume > 0:
                        logger.info("=== PERFORMING MANUAL ASPIRATION ===")
                        
                        # Move to aspiration position above the slide
                        asp_height = position.botton + 0.5
                        logger.info(f"Moving to aspiration position: ({position.x}, {position.y}, {asp_height})")
                        tools.mill.safe_move(position.x, position.y, asp_height, tool="pipette")
                        time.sleep(1)
                        
                        # Aspirate the volume from the slide
                        logger.info(f"Aspirating {position.volume} µL from slide position {position.name}")
                        tools.pipette.aspirate(position.volume)
                        time.sleep(1)
                        
                        # Move to waste vial position
                        waste_coords = vial_dest.coordinates
                        waste_height = waste_coords["z"] + 50  # Above waste vial
                        logger.info(f"Moving to waste position: ({waste_coords['x']}, {waste_coords['y']}, {waste_height})")
                        tools.mill.safe_move(waste_coords["x"], waste_coords["y"], waste_height, tool="pipette")
                        time.sleep(1)
                        
                        # Dispense into waste
                        logger.info(f"Dispensing {position.volume} µL into waste vial")
                        tools.pipette.dispense(position.volume)
                        time.sleep(1)
                        
                        logger.info("Manual aspiration completed successfully")
                        
                        # Update position volume after aspiration
                        position.remove_volume(position.volume)
                        logger.info(f"Position {position.name} now contains {position.volume} µL")
                    else:
                        logger.warning(f"No volume to aspirate from position {position.name}")
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
                    except Exception as cleanup_e:
                        logger.warning(f"Error while turning off lights during cleanup: {cleanup_e}")
                
                # Disconnect mill
                try:
                    if tools.mill:
                        
                        tools.mill.disconnect()
                except Exception as cleanup_e:
                    logger.error(f"Mill cleanup error: {cleanup_e}")
        except Exception as cleanup_e:
            logger.error(f"General cleanup error: {cleanup_e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.error(f"Experiment failed: {e}", exc_info=True)
    finally:
        # Your cleanup code here
        try:
            if 'tools' in locals():
                # Cleanup hardware connections
                pass
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
            logger.error(f"Cleanup error: {cleanup_error}", exc_info=True)