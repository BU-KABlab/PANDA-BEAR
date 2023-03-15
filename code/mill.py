import serial
import time

# configure the serial port
ser = serial.Serial()
ser.baudrate = 9600
ser.port = '/dev/ttyUSB0'  # set your port name here
ser.timeout = 1
ser.open()

# define some commands
home = "G28\n"  # home all axes
move_to = "G1 X{} Y{} Z{}\n"  # move to specified coordinates

# move to the starting position
ser.write(home.encode())
response = ser.readline().decode().strip()  # read the response
print(response)
time.sleep(5)  # wait for 5 seconds for the machine to home

# move to the target position
x, y, z = 40, 30, -20  # set target coordinates
ser.write(move_to.format(x, y, z).encode())
response = ser.readline().decode().strip()  # read the response
print(response)

# wait for the machine to finish moving
time.sleep(10)  # wait for 10 seconds

# stop the machine
ser.write(b'\x18')  # send the keyboard interrupt signal to stop the machine
response = ser.readline().decode().strip()  # read the response
print(response)

# close the serial port
ser.close()
