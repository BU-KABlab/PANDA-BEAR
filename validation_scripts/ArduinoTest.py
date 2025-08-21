import serial
import time

ser = serial.Serial("/dev/ttyACM1", 115200, timeout=1, rtscts=False, dsrdtr=False, xonxoff=False)
ser.setDTR(False)
ser.setRTS(False)
time.sleep(0.2)
ser.reset_input_buffer()
ser.reset_output_buffer()
time.sleep(0.1)

print("Sending CMD_EMAG_ON")
ser.write(b"5\n")
ser.flush()
time.sleep(0.5)

print("Sending CMD_EMAG_OFF")
ser.write(b"6\n")
ser.flush()
time.sleep(0.5)

ser.close()
print("Done")
