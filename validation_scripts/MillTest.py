import serial
import time

print("Opening connection to /dev/ttyUSB1...")
ser = serial.Serial("/dev/ttyUSB1", 115200, timeout=1)

time.sleep(2)  # Wait for GRBL to boot/reset
ser.reset_input_buffer()

print("Sending soft reset...")
ser.write(b"\x18")  # Ctrl-X soft reset
time.sleep(1)

print("Sending newline to wake up GRBL...")
ser.write(b"\r\n")
time.sleep(1)

print("Sending unlock command ($X)...")
ser.write(b"$X\n")
time.sleep(0.5)

print("Querying status (?)...")
ser.write(b"?\n")
time.sleep(0.5)

print("Reading response:")
while ser.in_waiting:
    print(ser.readline().decode(errors="ignore").strip())

ser.close()
print("Done.")
