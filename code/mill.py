import serial
import time

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
)


time.sleep(2)
command = 'G0x-20 0\n'# G00X80Y20\n'
#command = '(ctrl-x)\n'
print(f'Sending: {command}')
ser.write(command.replace(" ","").encode())

time.sleep(1)
#grbl_out = ser.readline()
#print(grbl_out)
out=''
while ser.inWaiting() > 0:
    out = ser.readline()
            
    if out != '':
        print(out.strip().decode())

ser.close()
