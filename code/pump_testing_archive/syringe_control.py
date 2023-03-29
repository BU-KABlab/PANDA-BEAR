import serial
import time

#define syringe attributes
syringes = {'1 ml BD':'4.699',
            '3 ml BD':'8.585',
            '10 ml BD':'14.60',
            '30ml BD':'21.59'}

#set up the serial port
serial_connection = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate= 19200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=5)

def find_pumps(ser,tot_range=1):
    pumps = []
    for i in range(tot_range):
        #pump_adr = str(i)
        cmd = 'ADR\r\n'
        print(f'Sending: ADR')
        ser.write(b"RUN\r")
        time.sleep(1)
        output = ser.readlines()
        print(f'Output: {output}')
        if len(output)>0:
            pumps.append(i)
        else:
            print(f'    No pump at address: 0{i}')
    return pumps

def run_all(ser):
    cmd = '*RUN\r\n'
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output: print (f'{cmd.strip()} from run_all not understood')

def stop_all(ser):
    cmd = '*STP\x0D'
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from stop_all not understood')

def stop_pump(ser,pump):
    cmd = str(pump +'STP\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from stop_pump not understood')

    cmd = str(pump+'RAT0UH\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from stop_pump not understood')

def set_rates(ser,rate):
    cmd = ''
    for pump in rate:
        flowrate = float(rate[pump])
        direction = 'INF'
        if flowrate<0: direction = 'WDR'
        frcmd = 'DIR' + direction * '\r\n'
        ser.write(str(frcmd).encode())
        output = ser.readline()
        if '?' in output: print (f'{frcmd.strip()} from set_rate not understood')
        fr = abs(flowrate)
                
        if fr<5000:
            cmd += str(pump)+'RAT'+str(fr)[:5]+'UH*'
        else:
            fr = fr/1000.0
            cmd += str(pump)+'RAT'+str(fr)[:5]+'MH*'
    cmd += '\x0D'
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from set_rates not understood')

def get_rate(ser,pump):
    #get direction
    cmd = str(pump+'DIR\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    sign = ''
    if output[4:7]=='WDR':
        sign = '-'
    cmd = str(pump+'RAT\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from get_rate not understood')
    units = output[-3:-1]
    if units=='MH':
        rate = str(float(output[4:-3])*1000)
    if units=='UH':
        rate = output[4:-3]
    return sign+rate

def get_rates(ser,pumps):
    rates = dict((p,get_rate(ser,p).split('.')[0]) for p in pumps)
    return rates

def set_diameter(ser,pump,dia):
    cmd = str(pump + 'DIA' + dia + '\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from set_diameter not understood')

    
def get_diameter(ser,pump):
    cmd =  str(pump+'DIA\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from get_diameter not understood')
    dia = output[4:-1]
    return dia

def prime(ser,pump):
    # set infuse direction
    cmd = str(pump+'DIRINF\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from prime not understood'
)
    # set rate
    cmd =  str(pump+'RAT10.0MH\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from prime not understood')

    # run
    cmd = str(pump +'RUN\x0D')
    ser.write(cmd.encode())
    output = ser.readline()
    if '?' in output: print (cmd.strip()+' from prime not understood')


serial_connection.open()
print (serial_connection.name)       # check which port was really used
print (f'Serial port is open: {serial_connection.isOpen()}')


pumps = find_pumps(serial_connection)
print(pumps)
#rates = get_rates(serial_connection,pumps)
#print(rates)
#response = run_all(serial_connection)
serial_connection.close()