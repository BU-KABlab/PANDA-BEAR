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
        """
        # Move to a safe position
        print("Moving to safe position...")
        mill.safe_move(
            x_coord=-80.0,
            y_coord=-39.0,
            z_coord=-52.0
        )
        print("Mill in safe position")
        """

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
