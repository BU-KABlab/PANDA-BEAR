import serial
import time

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
)
if not ser.is_open:
    ser.open()
time.sleep(2)
#command = 'G00X80Y20\n'
#command = '$X\n'
#command = '(ctrl-x)\n'
#command = '$H\n'
command = 'close'
#command = 'GOOZO\n'

if command != 'close':
    print(f'Sending: {command.strip()}')
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
