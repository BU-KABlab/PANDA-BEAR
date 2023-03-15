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
move = "G1 X{} Y{} Z{}\n"  # move to specified coordinates

# define reusable functions
def send_command(command):
    ser.write(command.encode())
    response = ser.readline().decode().strip()
    return response

def move_to_position(x, y, z):
    command = move.format(x, y, z)
    response = send_command(command)
    return response

# move to the starting position
send_command(home)
time.sleep(5)  # wait for 5 seconds for the machine to home

# move to the target position
x, y, z = 40, 30, -20  # set target coordinates
response = move_to_position(x, y, z)
print(response)

# wait for the machine to finish moving
time.sleep(10)  # wait for 10 seconds

# stop the machine
send_command(b'\x18')
response = ser.readline().decode().strip()  # read the response
print(response)

# close the serial port
ser.close()
