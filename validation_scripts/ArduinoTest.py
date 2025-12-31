import serial
import time

port = "/dev/ttyACM1"
ser = serial.Serial(
    port,
    115200,
    timeout=0.5,
    write_timeout=0.5,
    rtscts=False,
    dsrdtr=False,
    xonxoff=False,
)
ser.setDTR(False)
ser.setRTS(False)
time.sleep(0.3)
ser.reset_input_buffer()
ser.reset_output_buffer()
ser.write(b"5\n")
ser.flush()  # EMAG ON
time.sleep(0.5)
ser.write(b"6\n")
ser.flush()  # EMAG OFF
ser.close()
print("Script completed")
