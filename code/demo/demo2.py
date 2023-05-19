import serial
import time
import nesp_lib
from classes import Vial, Wells, Mill_Control

# define serial port connection for SainSmart Prover/GRBL

# define reusable functions for the mill

def move_center_to_position(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x, y, z)
    response = Mill_Control.send_to_mill(command)
    return response

def move_pipette_to_position(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x-45, y, z)
    response = Mill_Control.send_to_mill(command)
    return response

def move_electrode_to_position(x, y, z):
    '''
    INPUT: x,y,z coordinates as int or float to where you want the mill to move absolutely

    '''
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x+45, y, z)
    response = Mill_Control.send_to_mill(command)
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

def pump_infuse(volume:float,rate:float):
    '''Set the pump direction to infuse the given volume at the given rate
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Returns the cummulative volume infused when complete'''
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_volume = volume
    # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.pumping_rate = rate
    pump.run()
    return pump.volume_infused

# define location of items on the deck
v1 = Vial(10,10,20,1,'water',3)
v2 = Vial(10,15,20,1,'chlorine',3)
v3 = Vial(10,20,20,1,'PEG',3)

well_plate = Wells()
print(f'Well A1 coordinates {well_plate.get_coordinates("A1")}')
print(f'Well B6 coordinates {well_plate.get_coordinates("B6")}')
# begin by homing the mill
Mill_Control.home()

# begin procedure
move_center_to_position(30,20,-10)
response = pump_withdraw(0.25,0.5)
print(f'Pump has withdrawn: {response}ml')
move_center_to_position(30,25,-10)
response = pump_infuse(0.25,0.5)
print(f'Pump has infused: {response}ml')
print(f'remaining volume in pipette: {pump.volume_withdrawn}')
Mill_Control.home()