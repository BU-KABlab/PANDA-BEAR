import serial
import time
import nesp_lib
#from classes import Vial, Wells

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
            out = (out.strip().decode())
            print(out)
    else:
        ser.close()
        
    if command == '$H':
        time.sleep(20)
    else:
        time.sleep(10)
        
    return out
def MOVE_TO_POSITION(x, y, z,ser_mill):
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

def PUMP_WITHDRAW(volume:float,rate:float,ser_pump):
    '''Set the pump direction to withdraw the given volume at the given rate
        volume <float> (ml) | rate <float> (ml/m)
    
    Return the cummulative volue withdrawn when complete'''
    if ser_pump.volume_withdrawn + volume >= 0.1:
        Exception("The command will overfill the pipette. Not running")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        # Sets the pumping volume of the pump in units of milliliters.
        ser_pump.pumping_volume = volume
        # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.pumping_rate = rate
        ser_pump.run()
        while pump.running:
            pass
        time.sleep(2)
    return ser_pump.volume_withdrawn

def PUMP_INFUSE(volume:float,rate:float,pump):
    '''Set the pump direction to infuse the given volume at the given rate
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Returns the cummulative volume infused when complete'''
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_volume = volume
    # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.pumping_rate = rate
    pump.run()
    while pump.running:
        pass
    time.sleep(2)
    return pump.volume_infused

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

def SET_UP_PUMP():
    # set up WPI syringe pump
    pump_port = nesp_lib.Port('COM5',19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699 #milimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f'Pump at address: {pump.address}')
    return pump

try:
    # set up connection for SainSmart Prover/GRBL
    mill = SET_UP_MILL()
    if not mill.isOpen():
        mill.open()
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
    pump = SET_UP_PUMP()
    
    # begin by homing the mill
    SEND_COMMAND_TO_MILL(mill_home_cmd,mill)
    # tell the mill to use absolute positioning
    SEND_COMMAND_TO_MILL('G90',mill)
    # begin procedure
    #first operation
    MOVE_TO_POSITION(-30,-20,-10,mill)
    response = PUMP_WITHDRAW(0.02,0.2,pump)
    print(f'Pump has withdrawn: {response}ml')

    #second operation
    MOVE_TO_POSITION(-150,-25,-10,mill)
    response = PUMP_INFUSE(0.02,0.2,pump)

    print(f'Pump has infused: {response}ml')
    print(f'remaining volume in pipette: {pump.volume_withdrawn}')
    SEND_COMMAND_TO_MILL(mill_home_cmd,mill)
    mill.close()
finally:
    pass
   