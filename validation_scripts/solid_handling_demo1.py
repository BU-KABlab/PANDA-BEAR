"""
Solid Handling Demonstration Protocol

This script demonstrates solid handling capabilities including:
- Multiple Arduino connections (light ring, electromagnet, linebreak sensor)
- Decapping and capping operations
- Precise mill movement (rectangular pattern)
- Imaging with light control
- Interaction with gel surfaces
"""

import logging
from pathlib import Path
from datetime import datetime

# PANDA system imports
from panda_lib.hardware import PandaMill

# from panda_lib.hardware.panda_pipettes import Pipette, insert_newz h_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.types import VialKwargs
from panda_lib.labware.vials import StockVial
from panda_lib.actions.movement import capping_sequence

# Set up logging
logger = logging.getLogger("solid_handling_demo")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Create output directory
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
output_dir = Path(f"solid_handling_demo_{timestamp}")
output_dir.mkdir(exist_ok=True)

# Create file handler
file_handler = logging.FileHandler(output_dir / "solid_handling_demo.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Constants
vial_x = -20.1  # X coordinate for stock vial
vial_y = -74.3  # Y coordinate for stock vial
vial_z_touch = (
    -184.16
)  # Z coordinate for stock vial right above powder TODO update this before running
well_a1_z_touch = (
    -164.36
)  # Z coordinate for wellplate A1 (base level) TODO update this before running
safe_z = 0
well_x_init = -139.5  # X coordinate for wellplate A1 TODO update this before running
well_y_init = -80.2  # Y coordinate for wellplate A1 TODO update this before running
x_offset = -20.5  # X offset between wells
y_offset = -20.5  # Y offset between wells
wells = []
cols = "ABCDEF"
rows = [str(i) for i in range(1, 5)]

# Add this near the top of your script, after imports
DRY_RUN = False  # Set to False when you want to actually run the movements


# Create a class to replace the PandaMill for dry runs
class DryRunMill:
    """A mock mill that logs commands but doesn't move."""

    def __init__(self):
        self.current_position = {"x": 0, "y": 0, "z": 0}
        self.current_tool = None
        self.log_file = Path("dry_run_movements.csv")

        # Create log file with headers
        with open(self.log_file, "w") as f:
            f.write("command,x,y,z,tool,feed_rate,notes\n")

        print("[DRY RUN] MODE ACTIVE - No actual movements will occur")
        print(f"[LOG] Movement commands will be logged to: {self.log_file}")

    def log_movement(
        self, command, x=None, y=None, z=None, tool=None, feed_rate=None, notes=None
    ):
        """Log a movement command to CSV file."""
        with open(self.log_file, "a") as f:
            f.write(f"{command},{x},{y},{z},{tool},{feed_rate},{notes}\n")

        # Also print to console
        tool_str = f", tool: {tool}" if tool else ""
        position_str = ", ".join(
            [
                f"{axis}: {val}"
                for axis, val in [("x", x), ("y", y), ("z", z)]
                if val is not None
            ]
        )
        print(f"[DRY RUN] {command}: {position_str}{tool_str}")

        # Update current position
        if x is not None:
            self.current_position["x"] = x
        if y is not None:
            self.current_position["y"] = y
        if z is not None:
            self.current_position["z"] = z
        if tool is not None:
            self.current_tool = tool

    # Implement all the methods from PandaMill that your script uses
    def connect_to_mill(self):
        print("[DRY RUN] Would connect to mill")
        return True

    def homing_sequence(self):
        self.log_movement("homing", 0, 0, 0, notes="Homing sequence")
        return True

    def set_feed_rate(self, rate):
        self.log_movement("set_feed_rate", feed_rate=rate, notes="Set feed rate")
        return True

    def move_to_position(self, x=None, y=None, z=None, tool=None, **kwargs):
        self.log_movement(
            "move_to_position", x, y, z, tool, notes=str(kwargs) if kwargs else None
        )
        return True

    def safe_move(self, x=None, y=None, z=None, tool=None, **kwargs):
        # Check if x is actually a dictionary of coordinates
        if isinstance(x, dict) and "x" in x and "y" in x:
            coords = x
            x = coords.get("x")
            y = coords.get("y")
            z = coords.get("z")

        self.log_movement(
            "safe_move", x, y, z, tool, notes=str(kwargs) if kwargs else None
        )
        return True

    def move_to_safe_position(self):
        self.log_movement(
            "move_to_safe_position", 0, 0, 0, notes="Moving to safe position"
        )
        return True

    def disconnect(self):
        print("[DRY RUN] Would disconnect from mill")
        return True

    def send_command(self, command):
        self.log_movement("send_command", notes=command)
        return "OK"


# Add this class after your DryRunArduino class definition
class CoordinateObject:
    """Simple class to hold x, y, z coordinates with attribute access."""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


# Add this code before your "try" block
if DRY_RUN:
    # Replace actual hardware classes with dry run versions
    PandaMill = DryRunMill

    # Create a mock capping sequence that works around the bug
    def mock_capping_sequence(mill, coords, arduino, **kwargs):
        """Mock implementation of capping that works in dry run mode."""
        print("[DRY RUN] MOCK CAPPING: Would cap vial")

        # Log the movements
        mill.log_movement(
            "capping",
            coords.x,
            coords.y,
            coords.z,
            tool="decapper",
            notes="Start capping sequence",
        )
        mill.safe_move(coords.x, coords.y, coords.z, tool="decapper")

        # Simulate the ALL_CAP call
        arduino.ALL_CAP()

        # Move to safe position
        mill.move_to_position(coords.x, coords.y, 0, tool="decapper")

        # This is the part that's broken in the real function - we'll skip it
        print("[DRY RUN] SKIPPING problematic line break check in capping sequence")

        # Indicate success
        return True

    capping_sequence = mock_capping_sequence


def get_well_coordinates(well_id):
    """Input like A1, B2, return real x, y coordinates"""
    cols = "ABCDEF"
    rows = [str(i) for i in range(1, 5)]

    col = well_id[0].upper()
    row = well_id[1:]

    if col not in cols or row not in rows:
        raise ValueError(f"Invalid coordinate: {well_id}")

    x = well_x_init + x_offset * cols.index(col)
    y = well_y_init + y_offset * (int(row) - 1)
    return round(x, 3), round(y, 3)


try:
    # ===== HARDWARE SETUP =====
    logger.info("Initializing hardware components...")

    # Initialize the mill
    mill = PandaMill()

    # Create toolkit
    tools = Toolkit(
        mill=PandaMill(),
        arduino=arduino,
        global_logger=logger,
        use_mock_instruments=DRY_RUN,
    )

    logger.info("Successfully initialized hardware")
    # ===== LABWARE SETUP =====

    # Set up stock vial 1
    vkwargs_stock = VialKwargs(
        category=0,
        name="Solid_Sample",
        contents={"solid_particles": 10000},
        viscosity_cp=1,  # Not applicable for solids
        concentration=0.01,
        density=1,
        height=66,
        radius=14,
        volume=10000,  # TODO update this before running
        capacity=20000,
        contamination=0,
        coordinates={
            "x": vial_x,
            "y": vial_y,
            "z": -197.0,
        },
        base_thickness=1,
        dead_volume=0,
    )

    stock_vial = StockVial(position="s1", create_new=True, **vkwargs_stock)
    stock_vial.save()

    # ===== RECTANGULAR MOVEMENT PATTERN =====
    # Define rectangular movement pattern (adjust as needed)
    rect_pattern = [
        {"x": 0, "y": 0},  # Starting point (relative to vial center)
        {"x": 2, "y": 0},  # Right
        {"x": 2, "y": 2},  # Up
        {"x": 0, "y": 2},  # Left
        {"x": 0, "y": 0},  # Back to start
    ]

    # ===== EXECUTE PROTOCOL =====
    logger.info("Beginning solid handling protocol")

    # Home the mill
    logger.info("Homing mill...")
    mill.connect_to_mill()
    mill.homing_sequence()
    mill.set_feed_rate(3000)  # Slower for solid handling

    # # 1. Decap stock vial 1
    # logger.info("Decapping stock vial 1...")
    # decapping_sequence(
    #     mill,
    #     CoordinateObject(stock_vial.coordinates.x, stock_vial.coordinates.y, stock_vial.top),
    #     arduino
    # )

    while True:
        wells_input = input(
            "Input the well position (like A1 B2 C3) or measure the whole plate (all), Enter: "
        )

        # Log the user input
        logger.info(f"User input received: '{wells_input}'")

        if wells_input.strip() == "":
            logger.info("Empty input received, breaking input loop")
            break

        if wells_input.strip().lower() == "all":
            wells = [f"{c}{r}" for r in rows for c in cols]
            logger.info(f"Full plate handling selected: {wells}")
            print(f"Now measuring full plate: {wells}")
            break

        wells_list = wells_input.strip().split()
        valid_wells = []
        for well in wells_list:
            try:
                get_well_coordinates(well)  # Verify the input coordinates
                valid_wells.append(well.upper())
                logger.info(f"Valid well added: {well.upper()}")
            except ValueError as e:
                logger.warning(f"Invalid well coordinate: {well} - {e}")
                print(e)
        wells.extend(valid_wells)
        logger.info(f"Current valid wells list: {wells}")
        print(f"Now valid wells: {wells}")

    # TODO: fix this to make sure back to the stock each time
    for well in wells:
        # 2. Move pipette to stock vial 1
        logger.info("Moving pipette back to the stock")
        mill.safe_move(
            stock_vial.coordinates.x,
            stock_vial.coordinates.y,
            stock_vial.bottom + 80,  # Position above vial
            tool="pipette",
        )

        # 3. Lower pipette into stock vial
        logger.info("Lowering pipette into stock vial...")
        mill.safe_move(
            stock_vial.coordinates.x,
            stock_vial.coordinates.y,
            vial_z_touch,  # TODO upddate this before running
            tool="pipette",
        )

        # # 4. Move in rectangular pattern
        # logger.info("Executing rectangular movement pattern...")
        # base_x = stock_vial.coordinates.x
        # base_y = stock_vial.coordinates.y
        # base_z = vial_z_touch  # TODO update this before running

        # for point in rect_pattern:
        #     target_x = base_x + point["x"]
        #     target_y = base_y + point["y"]
        #     logger.info(f"Moving to relative position: ({point['x']}, {point['y']})")
        #     mill.move_to_position(target_x, target_y, base_z, tool="pipette")

        # 5. Raise pipette up
        logger.info("Raising pipette...")
        mill.safe_move(
            stock_vial.coordinates.x,
            stock_vial.coordinates.y,
            stock_vial.bottom + 80,
            tool="pipette",
        )

        # 6. Cap the stock vial

        # 7. Move pipette to wellplate
        well_a1_x, well_a1_y = get_well_coordinates(well)
        logger.info(f"Moving to wellplate position: {well}")
        mill.safe_move(
            well_a1_x,
            well_a1_y,
            stock_vial.bottom + 80,  # Position above well
            tool="pipette",
        )

        # 8. Lower pipette to touch gel surface
        logger.info(f"Lowering pipette to gel surface: {well}")
        mill.move_to_position(
            well_a1_x,
            well_a1_y,
            well_a1_z_touch,  # little bit above the solvent base
            tool="pipette",
        )

        # 10. Raise pipette to safe position
        logger.info("Moving to safe position...")
        mill.move_to_safe_position()

        input("Please Enter to continue if cleaning is done:")

    # Protocol complete
    logger.info("Solid handling protocol completed successfully")

except Exception as e:
    logger.error(f"Protocol failed: {e}", exc_info=True)
    print(f"An error occurred: {e}")

finally:
    # Cleanup
    try:
        # Disconnect from hardware
        if "mill" in locals():
            mill.disconnect()
            logger.info("Mill disconnected")

        print("Hardware disconnected. Protocol completed.")
        logger.info("Cleanup completed")

    except Exception as cleanup_error:
        print(f"Error during cleanup: {cleanup_error}")
        logger.error(f"Cleanup error: {cleanup_error}", exc_info=True)
