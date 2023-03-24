
import serial
import time
import math

# configure the serial ports
ser_pump = serial.Serial()
ser_pump.baudrate = 19200
ser_pump.port = '/dev/ttyUSB0'  # set your pump port name here
ser_pump.timeout = 1
ser_pump.open()

#ser_mill = serial.Serial(
#    port='/dev/ttyUSB1',
#    baudrate=115200,
#    parity=serial.PARITY_NONE,
#    stopbits=serial.STOPBITS_ONE,
#    bytesize=serial.EIGHTBITS,
#)
#ser_mill.open()


# define some commands
pump_infuse = "INF{}\n"  # infuse command for the pump
pump_withdraw = "IW{}\n"  # withdraw command for the pump
mill_home = "$H\n"  # home all axes
mill_move = "G0 X{} Y{} Z{}\n"  # move to specified coordinates

# define some constants
steps_per_rev = 200  # steps per motor revolution
microsteps_per_step = 8  # microsteps per motor step
lead_screw_pitch = 1.5875  # millimeters of travel per motor revolution
syringe_diameter = 4.57  # syringe diameter in millimeters

# define reusable functions for the mill
def send_mill_command(command):
    print(f'Sending {command} to mill')
    ser_mill.write(command)
    response = ser_mill.readline().decode().strip()
    return response

def move_to_position(x, y, z):
    command = mill_move.format(x, y, z)
    response = send_mill_command(command.encode())
    return response

def calculate_steps(distance):
    # calculate the number of steps needed to move the specified distance
    steps = distance / (lead_screw_pitch * microsteps_per_step) * steps_per_rev
    return int(steps)

# define reusable functions for the syringe pump
def send_pump_command(command):
    print(f'Sending {command} to pump')
    ser_pump.write(command)
    response = ser_pump.readline().decode().strip()
    print(response)
    return response

def calculate_volume(distance):
    # calculate the volume of fluid displaced by the specified distance
    radius = syringe_diameter / 2
    area = math.pi * radius ** 2
    volume = area * distance
    return volume

def infuse(volume):
    distance = volume / calculate_volume(1)  # calculate the distance to move
    steps = calculate_steps(distance)  # calculate the number of steps to move
    command = pump_infuse.format(steps)
    response = send_pump_command(command.encode())
    return response

def withdraw(volume):
    distance = volume / calculate_volume(1)  # calculate the distance to move
    steps = calculate_steps(distance)  # calculate the number of steps to move
    command = pump_withdraw.format(steps)
    response = send_pump_command(command.encode())
    return response

# move to the starting position
#response = send_mill_command(mill_home.encode())
#print(response)
#time.sleep(30)  # wait for 5 seconds for the machine to home

# move to the target position
#x, y, z = 40, 30, -20  # set target coordinates
#response = move_to_position(x, y, z)
#print(response)
#time.sleep(10)

# infuse 0.5 ml of fluid
#volume = 10  # set the infusion volume
#response = infuse(volume)
response = send_pump_command(b'INF')
print(response)

time.sleep(10)

# withdraw 0.2 ml of fluid
#volume = 0.2  # set the withdrawal volume
#response = withdraw(volume)
#print(response)

# wait for the machine to finish moving
time.sleep(10)
#ser_mill.close()
ser_pump.close()
