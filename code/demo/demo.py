import serial
import time
import nesp_lib
from classes import Vial, Wells

# define reusable functions for the mill
def SEND_COMMAND_TO_MILL(command:str,ser):
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
def MOVE_TO_POSITION(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G00 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x, y, z)
    response = SEND_COMMAND_TO_MILL(command,ser_mill)
    return response

def MOVE_TO_PIPETTE_TO_POSITION(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x-45, y, z)
    response = SEND_COMMAND_TO_MILL(command,ser_mill)
    return response

def MOVE_ELECTRODE_TO_POSITION(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x+45, y, z)
    response = SEND_COMMAND_TO_MILL(command,ser_mill)
    return response

def PUMP_WITHDRAW(volume:float,rate:float,pump):
    '''Set the pump direction to withdraw the given volume at the given rate
        volume <float> (ml) | rate <float> (ml/m)
    
    Return the cummulative volue withdrawn when complete'''
    if pump.volume_withdrawn + volume >= 0.1:
        Exception("The command will overfill the pipette. Not running")
    else:
        pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        # Sets the pumping volume of the pump in units of milliliters.
        pump.pumping_volume = 0.02
        # Sets the pumping rate of the pump in units of milliliters per minute.
        pump.pumping_rate = 0.1
        pump.run()
    return pump.volume_withdrawn

def PUMP_INFUSE(volue:float,rate:float,pump):
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

def SET_UP_PUMP():
    # set up WPI syringe pump
    pump_port = nesp_lib.Port('COM5',19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699 #milimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f'Pump at address: {pump.address}')
    return pump

def SET_UP_MILL():
    ser_mill = serial.Serial(
        port= 'COM4',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
    return ser_mill

try:
    # set up connection for SainSmart Prover/GRBL
    ser_mill = SET_UP_MILL()
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

    #set up the WPI syringe pump
    ser_pump = SET_UP_PUMP()
    if not ser_pump.isOpen():
        ser_pump.open()
    time.sleep(2)
    
    # begin by homing the mill
    SEND_COMMAND_TO_MILL(mill_home_cmd)
    # tell the mill to use absolute positioning
    SEND_COMMAND_TO_MILL('G90')
    # begin procedure
    #first operation
    MOVE_TO_POSITION(30,20,-10)
    response = PUMP_WITHDRAW(0.25,0.5,ser_pump)
    print(f'Pump has withdrawn: {response}ml')

    #second operation
    MOVE_TO_POSITION(30,25,-10)
    response = PUMP_INFUSE(0.25,0.5,ser_pump)

    print(f'Pump has infused: {response}ml')
    print(f'remaining volume in pipette: {ser_pump.volume_withdrawn}')
    SEND_COMMAND_TO_MILL(mill_home_cmd)
finally:
    ser_mill.close()
    ser_pump.close()