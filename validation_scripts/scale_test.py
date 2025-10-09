import sys
import os
import logging
import time

# Add logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("panda.scale")

# Import the custom scale
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from panda_lib.hardware.custom_scale import CustomScale

def test_scale_debug():
    """Test the scale with extensive debugging."""
    print("Scale debugging - please follow the steps:")
    
    # Create scale connection
    scale = CustomScale("/dev/ttyUSB0", baudrate=19200)
    
    # First, clear the scale
    print("\n1. PLEASE CLEAR THE SCALE COMPLETELY")
    input("   Press Enter when the scale is empty...")
    
    # Get multiple readings of the empty scale
    print("\n2. Reading empty scale:")
    for i in range(3):
        scale.get()
        time.sleep(1)
        
    # Now add a known weight
    print("\n3. PLEASE ADD A KNOWN WEIGHT (e.g., 100g)")
    weight_value = input("   Enter the actual weight you added (in grams): ")
    print(f"   Added {weight_value}g to the scale")
    
    # Get multiple readings with the weight
    print("\n4. Reading scale with weight:")
    for i in range(3):
        scale.get()
        time.sleep(1)
        
    # Now add another weight
    print("\n5. PLEASE ADD ANOTHER KNOWN WEIGHT")
    weight_value2 = input("   Enter the additional weight you added (in grams): ")
    print(f"   Added another {weight_value2}g (total {float(weight_value) + float(weight_value2)}g)")
    
    # Get more readings
    print("\n6. Reading scale with additional weight:")
    for i in range(3):
        scale.get()
        time.sleep(1)
        
    print("\nDebug session complete. Check the log output to determine the correct parsing method.")
    scale.disconnect()

if __name__ == "__main__":
    test_scale_debug()