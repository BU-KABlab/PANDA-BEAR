import serial
import time

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

time.sleep(2)
test_command = 'G00X80Y20'
stop_cmd = '$X'
reset_cmd = '(ctrl-x)'
home_cmd = '$H'
close_cmd = 'close'
current_status_cmd = '?'
check_gcode_mode = '$C'
check_gcode_params = '$#'
gcode_parser_state = '$G'




def send_command_to_mill(command):
    if command != 'close':
        print(f'Sending: {command.strip()}')
        command = command + '\n'
        ser.write(command.replace(" ","").encode())

        time.sleep(1)
        #grbl_out = ser.readline()
        #print(grbl_out)
        out=''
        while ser.inWaiting() > 0:
            out = ser.readline()
                    
            if out != '':
                print(out.strip().decode())
    else:
        ser.close()

send_command_to_mill(home_cmd)
command = 'G90 G00 X20Y20'
send_command_to_mill(command)

time.sleep(5)
send_command_to_mill(command)