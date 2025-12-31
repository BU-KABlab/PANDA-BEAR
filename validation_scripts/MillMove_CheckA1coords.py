import logging
from panda_lib.hardware import PandaMill

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("panda")


def home_mill():
    """Simple script to home the mill and disconnect."""
    print("Initializing mill...")
    mill = PandaMill()

    try:
        # Connect to the mill
        print("Connecting to mill...")
        mill.connect_to_mill()

        # Home the mill
        print("Homing mill...")
        mill.homing_sequence()
        print("Mill successfully homed!")

        # variables
        pipette_x_offset = -115.9
        pipette_y_offset = -6.1
        pipette_z_offset = 100

        coords = {"x": -269.5, "y": -154.4, "z": -185}

        coords_x, coords_y, coords_z = coords["x"], coords["y"], coords["z"]

        x_coord = coords_x + pipette_x_offset
        y_coord = coords_y + pipette_y_offset
        z_coord = coords_z + pipette_z_offset

        # Move to front corner for PAW maintenance
        print("Checking well coordinates.")
        mill.safe_move(x_coord=x_coord, y_coord=y_coord, z_coord=z_coord)
        print("Mill in well position")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect from the mill
        print("Disconnecting from mill...")
        mill.disconnect()
        print("Mill disconnected")


if __name__ == "__main__":
    home_mill()
    print("Script completed")
