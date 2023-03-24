import serial
import time

# configure the serial port
ser = serial.Serial(
    port='/dev/ttyUSB1',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
)

# define some commands
home = "$H\n"  # home all axes
move = "G0 X{} Y{} Z{}\n"  # move to specified coordinates

# define reusable functions
def send_command(command):
    print(f'Sending: {command}')
    ser.write(command)
    response = ser.readline().decode().strip()
    return response

def move_to_position(x, y, z):
    command = move.format(x, y, z).encode()
    response = send_command(command)
    return response

# move to the starting position
response = send_command(b'$H\n')
print(response)
time.sleep(5)  # wait for 5 seconds for the machine to home

# move to the target position
x, y, z = 40, 30, -20  # set target coordinates
response = move_to_position(x, y, z)
print(response)

# wait for the machine to finish moving
time.sleep(10)  # wait for 10 seconds
move_to_position(20,20,0)

time.sleep(10)  # wait for 10 seconds
move_to_position(20,20,0)
time.sleep(10)  # wait for 10 seconds


# stop the machine
send_command(b'\x18')
response = ser.readline().decode().strip()  # read the response
print(response)

# close the serial port
ser.close()
