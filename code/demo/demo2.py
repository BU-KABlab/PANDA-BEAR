import time
import nesp_lib
from classes import Vial, Wells, MillControl

def set_up_pump():
    # Set up WPI syringe pump
    pump_port = nesp_lib.Port('COM5', 19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699  # millimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f'Pump at address: {pump.address}')
    return pump

def withdraw(volume: float, rate: float, ser_pump):
    '''Set the pump direction to withdraw the given volume at the given rate.
    volume <float> (ml) | rate <float> (ml/m)
    Return the cumulative volume withdrawn when complete.
    '''
    if ser_pump.volume_withdrawn + volume >= 0.2:
        raise Exception("The command will overfill the pipette. Not running")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        ser_pump.pumping_volume = volume  # Sets the pumping volume of the pump in units of milliliters.
        ser_pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.run()
        while ser_pump.running:
            pass
        time.sleep(2)
        print(f'Pump has withdrawn: {ser_pump.volume_withdrawn} ml')
    return 0

def infuse(volume: float, rate: float, pump):
    '''Set the pump direction to infuse the given volume at the given rate.
    volume <float> (ml) | rate <float> (ml/m)
    Returns the cumulative volume infused when complete.
    '''
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    pump.pumping_volume = volume  # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.run()
    while pump.running:
        pass
    time.sleep(2)
    print(f'Pump has infused: {pump.volume_infused} ml')
    return 0
purge = infuse

# Define location of items on the deck
v1 = Vial(-10, -10, -20, 1, 'water', 3)
v2 = Vial(-10, -15, -20, 1, 'chlorine', 3)
v3 = Vial(-10, -20, -20, 1, 'PEG', 3)
wells = Wells(-200, -200, 0)

with MillControl() as mill:
    pump = set_up_pump()

    def move_center_to_position(x, y, z):
        '''
        INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
        '''
        mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(x, y, z)
        response = mill.send_to_mill(command)
        return response

    def move_pipette_to_position(x, y, z):
        '''
        INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
        '''
        mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(x - 45, y, z)
        response = mill.send_to_mill(command)
        return response

    def move_electrode_to_position(x, y, z):
        '''
        INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
        '''
        mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(x + 45, y, z)
        response = mill.send_to_mill(command)
        return response

    # Begin by homing the mill
    mill.home()
    # Begin procedure
    move_center_to_position(30, 20, -10)
    response = withdraw(0.14, 0.5, pump)
    purge(0.02,0.5,pump)
    move_center_to_position(30, 25, -10)
    infuse(0.1,0.5,pump)
    print(f'Remaining volume in pipette: {pump.volume_withdrawn}')
    mill.home()
