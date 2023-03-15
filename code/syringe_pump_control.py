import serial
import time

# configure the serial port
ser = serial.Serial()
ser.baudrate = 9600
ser.port = '/dev/ttyUSB0'  # set your port name here
ser.timeout = 1
ser.open()

# define some commands
pump_rate = "IRATE,1,0.5\r\n"  # set pump rate to 0.5 ml/min
syringe_diameter = "IDIAM,1,4.0\r\n"  # set syringe diameter to 4.0 mm
infuse = "INFU,1,10\r\n"  # infuse 10 ml

# send the commands to the pump
ser.write(pump_rate.encode())
ser.write(syringe_diameter.encode())
ser.write(infuse.encode())

# wait for the pump to finish infusing
time.sleep(60)  # wait for 1 minute

# stop the pump
stop = "STOP\r\n"
ser.write(stop.encode())

# close the serial port
ser.close()

