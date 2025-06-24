import os
import sys
import logging
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("panda")

# Import Arduino interface directly
from panda_lib.hardware.arduino_interface import ArduinoLink, PawduinoFunctions

def test_arduino_pipette():
    """Test pipette functions directly through Arduino commands."""
    print("=== ARDUINO PIPETTE TEST SCRIPT ===")
    
    # Define Arduino port - adjust as needed
    arduino_port = "/dev/ttyACM1"  # Modify if your Arduino is on a different port
    
    try:
        print(f"Connecting to Arduino on {arduino_port}...")
        arduino = ArduinoLink(arduino_port)
        print("Arduino connected successfully")
        
        # Test basic communication
        print("\n=== Testing Arduino Communication ===")
        response = arduino.send(PawduinoFunctions.CMD_HELLO)
        print(f"Hello response: {response}")
        
        # Get initial status
        print("\n=== Getting Pipette Status ===")
        status_response = arduino.send(PawduinoFunctions.CMD_PIPETTE_STATUS)
        print(f"Status response: {status_response}")
        
        # Home the pipette
        print("\n=== Homing Pipette ===")
        home_response = arduino.send(PawduinoFunctions.CMD_PIPETTE_HOME)
        print(f"Home response: {home_response}")
        
        # Move to zero position (30mm is typical for P300)
        print("\n=== Moving to Zero Position ===")
        move_response = arduino.send(PawduinoFunctions.CMD_PIPETTE_MOVE_TO, 30, 2500)
        print(f"Move response: {move_response}")
        
        # Test aspirate
        print("\n=== Testing Aspirate ===")
        aspirate_response = arduino.send(PawduinoFunctions.CMD_PIPETTE_ASPIRATE, 100, 2500)
        print(f"Aspirate response: {aspirate_response}")
        time.sleep(2)
        
        # Test dispense
        print("\n=== Testing Dispense ===")
        dispense_response = arduino.send(PawduinoFunctions.CMD_PIPETTE_DISPENSE, 100, 2500)
        print(f"Dispense response: {dispense_response}")
        time.sleep(2)
        
        # Get final status
        print("\n=== Getting Final Pipette Status ===")
        final_status = arduino.send(PawduinoFunctions.CMD_PIPETTE_STATUS)
        print(f"Final status: {final_status}")
        
        print("\n=== Arduino Pipette Test Complete ===")
        
    except Exception as e:
        print(f"Error during Arduino pipette test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            # Disconnect from Arduino
            arduino.disconnect()
            print("Arduino disconnected")
        except Exception as e:
            print(f"Error disconnecting: {e}")

if __name__ == "__main__":
    test_arduino_pipette()