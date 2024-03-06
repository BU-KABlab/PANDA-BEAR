import serial
import time

# configure the serial port
ser = serial.Serial(
    port='COM6',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
)
if not ser.is_open:
    ser.open()
else:
    print('Serial port is still open')

time.sleep(2) #REQUIRED after opening the serial port to allow back and forth!!!

# define some commands
home_cmd = '$H\n' # home all axes
move = "G0 X{} Y{} Z{}\n"  # move to specified coordinates

# define reusable functions
def send_command_to_mill(command):
    if command != 'close':
        print(f'Sending: {command.strip()}')
        ser.write(command)
        time.sleep(1)
        out=''
        while ser.inWaiting() > 0:
            out = ser.readline()
                    
            if out != '':
                print(out.strip().decode())
    else:
        ser.close()

def move_to_position(x, y, z):
    command = move.format(x, y, z).encode()
    response = send_command_to_mill(command)
    return response

# move to the starting position
send_command_to_mill(home_cmd.encode())
#print(response)
time.sleep(10)  # wait for 10 seconds for the machine to home

# move to the target position
x, y, z = 40, 30, -20  # set target coordinates
move_to_position(x, y, z)
# wait for the machine to finish moving
time.sleep(10)  # wait for 10 seconds

move_to_position(20,20,0)
time.sleep(10)  # wait for 10 seconds

move_to_position(20,20,0)
time.sleep(10)  # wait for 10 seconds

move_to_position(0,0,0)
time.sleep(10)
# stop the machine
response = send_command_to_mill(b'\x18')# read the response
print(response)

# close the serial port
ser.close()
