
import serial
import time
import math
import nesp_lib

# find serial port devices
def find_serial_device(baudrate:int,OS:str):
    ''' Cycles through 40 ports to find a serial device matching the given baudrate.
        baudrate ex: 19200 for pump
        OS can be 'linux' or 'windows' 
        Returns: port_name or 'error' if no matching device found
    '''
    i = 0
    device_found = 0
    while i < 40:
        try:
            ser = serial.Serial()
            ser.baudrate = baudrate
            
            #choose the appropriate port naming based on operating system (OS)
            if OS == 'linux':
                port_name = '/dev/ttyUSB%i'%i
                ser.port = port_name  # set your pump port name here
            else:
                port_name = 'COM%i'%i
                ser.port = port_name
            ser.timeout = 1
            ser.open()
            
        except:
            #print(f'No pump at COM{i}')
            i += 1
            pass
        else:
            print(f'found a serial device at {port_name}')
            port_name = port_name
            device_found = 1
            i += 1
            ser.close()
    
    if device_found:
        return port_name
    else:
        return 'error'

# Check that the search for devices was fruitful
#pump_port= find_serial_device(19200,'windows')
#if pump_port == 'error': exit()
#mill_port = find_serial_device(115200,'windows')
#if mill_port == 'error': exit()

# define serial port connection for SainSmart Prover/GRBL
ser_mill = serial.Serial(
    port= 'COM6',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )
# define serial port connection for WPI syringe pump
ser_pump = serial.Serial(
    port = 'COM5',
    baudrate = 19200,
    timeout = 1,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    )

ser_pump.close()
ser_pump.open()
time.sleep(2)
ser_mill.close()
ser_mill.open()
time.sleep(2)

# define some commands
pump_infuse = "INF{}"  # infuse command for the pump
pump_withdraw = "IW{}"  # withdraw command for the pump
pump_address = "ADR"
pump_run = "RUN"
pump_stop = "STP"
mill_home = '$H'  # home all axes
mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates

# define some constants
steps_per_rev = 200  # steps per motor revolution
microsteps_per_step = 8  # microsteps per motor step
lead_screw_pitch = 1.5875  # millimeters of travel per motor revolution
syringe_diameter = 4.57  # syringe diameter in millimeters

# define reusable functions for the mill
def send_command_to_mill(command,ser):
    if command != 'close':
        print(f'Sending: {command.strip()}')
        ser.write(str(command+'\n').encode())
        time.sleep(1)
        out=''
        while ser.inWaiting() > 0:
            out = ser.readline()
                    
        if out != '':
            print(out.strip().decode())
    else:
        ser.close()

def move_to_position(x, y, z):
    command = mill_move.format(x, y, z)
    response = send_command_to_mill(command,ser_mill)
    return response

# define reusable functions for the syringe pump
def calculate_steps(distance):
    # calculate the number of steps needed to move the specified distance
    steps = distance / (lead_screw_pitch * microsteps_per_step) * steps_per_rev
    return int(steps)

def send_pump_command(command):
    print(f'Sending {command} to pump')
    encoded_cmd = str(command+'\r').encode()
    ser_pump.write(encoded_cmd)
    response = ser_pump.readline().decode(encoding="ascii").strip()
    print(f'pump returned: {response}')
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
send_command_to_mill(mill_home,ser_mill)
time.sleep(15)  # wait for 5 seconds for the machine to home

# move to the target position
x, y, z = 40, 30, -20  # set target coordinates
move_to_position(x, y, z)
time.sleep(10)

# infuse 0.1 ml of fluid
#volume = 10  # set the infusion volume
#response = infuse(volume)
send_pump_command(pump_address)
time.sleep(5)

# withdraw 0.2 ml of fluid
#volume = 0.2  # set the withdrawal volume
#withdraw(volume)
#print(response)

# wait for the machine to finish moving
time.sleep(10)
ser_mill.close()
ser_pump.close()
