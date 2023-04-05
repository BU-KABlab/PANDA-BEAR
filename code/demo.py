import serial
import time
import math
import nesp_lib

# define serial port connection for SainSmart Prover/GRBL
ser_mill = serial.Serial(
    port= 'COM6',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )
if not ser_mill.isOpen():
    ser_mill.open()
time.sleep(2)

# Mill commands
mill_stop_cmd = '$X'
mill_reset_cmd = '(ctrl-x)'
mill_home_cmd = '$H'
mill_current_status_cmd = '?'
mill_check_gcode_mode = '$C'
mill_check_gcode_params = '$#'
mill_gcode_parser_state = '$G'

# define reusable functions for the mill
def send_command_to_mill(command:str,ser):
    '''INPUT: 
        command: "command to send"
        ser: serial variable for the mill
    OUTPUT: Returns the response from the mill'''
    if command != 'close':
        print(f'Sending: {command.strip()}')
        ser.write(str(command+'\n').encode())
        time.sleep(1)
        out=''
        while ser.inWaiting() > 0:
            out = ser.readline()
                    
        if out != '':
            response = (out.strip().decode())
    else:
        ser.close()
    time.sleep(15)    
    return response
def move_to_position(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x, y, z)
    response = send_command_to_mill(command,ser_mill)
    return response


# set up WPI syringe pump
pump_port = nesp_lib.Port('COM5',19200)
pump = nesp_lib.Pump(pump_port)
pump.syringe_diameter = 4.699 #milimeters
pump.volume_infused_clear()
pump.volume_withdrawn_clear()
print(f'Pump at address: {pump.address}')

def pump_withdraw(volume:float,rate:float):
    '''Set the pump direction to withdraw the given volume at the given rate
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Return the cummulative volue withdrawn when complete'''
    pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
    # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_volume = 0.25
    # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.pumping_rate = 0.5
    pump.run()
    return pump.volume_withdrawn

def pump_infuse(volue:float,rate:float):
    '''Set the pump direction to infuse the given volume at the given rate
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Returns the cummulative volume infused when complete'''
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_volume = 0.25
    # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.pumping_rate = 0.5
    pump.run()
    return pump.volume_infused

#begin by homing the mill
send_command_to_mill(mill_home_cmd)

#begin procedure
move_to_position(30,20,-10)
response = pump_withdraw(0.25,0.5)
print(f'Pump has withdrawn: {response}ml')
move_to_position(30,25,-10)
response = pump_infuse(0.25,0.5)
print(f'Pump has infused: {response}ml')
print(f'remaining volume in pipette: {pump.volume_withdrawn}')