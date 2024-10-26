import pyvisa
import time

# Initialize VISA resource manager
rm = pyvisa.ResourceManager()
resource_name = "USB::0x1234::0x5678::INSTR"  # Replace with your device's actual VISA resource string
instr = rm.open_resource(resource_name)

def setup_chronoamperometry(voltage, duration):
    # Send initialization commands to set up chronoamperometry
    instr.write(f"FUNC:MODE CHRONO")
    instr.write(f"SOURCE:VOLT {voltage}")    # Set target voltage
    instr.write(f"TIME:DURATION {duration}")  # Set test duration
    instr.write("INIT")                      # Start the test

def read_data():
    # Read data periodically (depends on your sampling interval)
    data = []
    while True:
        try:
            current = instr.query("MEASURE:CURRENT?")
            timestamp = time.time()
            data.append((timestamp, float(current)))
            time.sleep(0.1)  # Adjust based on desired sampling rate
        except pyvisa.errors.VisaIOError:
            break
    return data

# Configure and run the test
setup_chronoamperometry(voltage=0.5, duration=60)  # 0.5V for 60 seconds
results = read_data()

# Output or further process the data
for timestamp, current in results:
    print(f"Time: {timestamp:.2f} s, Current: {current:.6f} A")
