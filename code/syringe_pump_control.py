import time
import serial

# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial(
    port='/dev/ttyUSB1',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)

ser.isOpen()

print('Enter your commands below.\r\nInsert "exit" to leave the application.')

input=1
while 1 :
    # get keyboard input
    input = input(">> ")

    if input == 'exit':
        ser.close()
        exit()
    else:
        # send the character to the device
        # (note that I append a \r\n carriage return and line feed to the characters - this is requested by my device)
        ser.write(input)
        out = ''
        # let's wait one second before reading output (let's give device time to answer)
        time.sleep(1)
        while ser.inWaiting() > 0:
            out += ser.read(1)
            
        if out != '':
            print(f">>{out}")

# return pump to Basic mode: (0x2) ( 0x8) SAF0 (0x55) (0x43) (0x3)