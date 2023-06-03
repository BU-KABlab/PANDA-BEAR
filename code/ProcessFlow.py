import time
import nesp_lib
import serial
from classes import Vial, Wells, MillControl
#HQ potentiostat#
#import demo.pstatcontrol

def set_up_pump():
    # Set up WPI syringe pump
    pump_port = nesp_lib.Port("COM5", 19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699  # millimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f"Pump at address: {pump.address}")
    time.sleep(2)
    return pump

def set_up_mill():
    ser_mill = serial.Serial(
        port= 'COM4',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
    time.sleep(2)
    return ser_mill


def withdraw(volume: float, position: list, depth: float, rate: float, ser_pump):
    """Set the pump direction to withdraw the given volume at the given rate and height.
    volume <float> (ml)
    
    position <list> coordinates x,y,z

    depth <float> <mm>
    
    rate <float> (ml/m)
    
    ser_pump <serial object to a pump>
    
    """
    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position["x"], position["y"], 0) #start above the location
    
    move_pipette_to_position(position["x"], position["y"], position["z"]) # go to the top
    
    move_pipette_to_position(position["x"], position["y"], position["z"] + depth) # plunge a calculated depth
    
    # Perform the withdrawl
    if ser_pump.volume_withdrawn + volume >= 0.2:
        raise Exception("The command will overfill the pipette. Not running")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        ser_pump.pumping_volume = (volume)  # Sets the pumping volume of the pump in units of milliliters.
        ser_pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.run()
        while ser_pump.running:
            pass
        time.sleep(2)
        print(f"Pump has withdrawn: {ser_pump.volume_withdrawn} ml")

    # Return to safe height
    move_pipette_to_position(position["x"], position["y"], 0)
    mill.current_status()
    return 0


def infuse(volume: float, position: list, depth: float, rate: float, pump):
    """Set the pump direction to infuse the given volume at the given rate.
    volume <float> (ml) | rate <float> (ml/m)
    """
    move_pipette_to_position(position["x"], position["y"],0) #first move to the x,y coord
    mill.current_status()

    move_pipette_to_position(position["x"], position["y"], position["z"]) # then lower to the top
    mill.current_status()

    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position["x"], position["y"], position["z"] + depth) #then lower to the pipetting depth
    mill.current_status()
    # Perform infusion
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    pump.pumping_volume = (
        volume  # Sets the pumping volume of the pump in units of milliliters.
    )
    pump.pumping_rate = (
        rate  # Sets the pumping rate of the pump in units of milliliters per minute.
    )
    pump.run()
    while pump.running:
        pass
    time.sleep(2)
    print(f"Pump has infused: {pump.volume_infused} ml")

    # Move the pipette back up
    move_pipette_to_position(position["x"], position["y"], 0)
    mill.current_status()
    return 0


def move_center_to_position(coordinates: list):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(coordinates["x"], coordinates["y"], coordinates["z"])
    response = mill.execute_command(command)
    return response


def move_pipette_to_position(x,y,z):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x - 84, y, z)  # x-coordinate has 84 mm offset for pipette location
    response = mill.execute_command(str(command))
    return response


def move_electrode_to_position(coordinates : list):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(coordinates['x'] + 84.5, coordinates['y'], coordinates['z'])  # electrode has 84.5 mm offset
    response = mill.execute_command(str(command))
    return response


""" 
-------------------------------------------------------------------------
Program Set Up
-------------------------------------------------------------------------
"""
mill = MillControl(set_up_mill())


# Set up the pump
pump = set_up_pump()
# Define the amount to purge, vial location, height,and rate to purge
purge_vial = Vial(0,-200,0,-36,'waste',0)
#purge = infuse(20, purge_vial.coordinates, -30, 0.4, pump)
purge = infuse
# Common values
# TODO eliminate these values by calculating the volume/depth for each vessel based on their z-top and bottom
withdrawl_height = -30
infuse_height = withdrawl_height

# Set up wells
plate = Wells(-200, -100, 0)
#floor-of-well = -##

# Define locations of vials and their contents
Solution1 = Vial(0, -100, 0, -36, "water", 400)
# Define the amount to purge, vial location, height,and rate to purge
purge_vial = Vial(0,-200,0,-36,'waste',0)
DMF = Vial(0, -150, 0 , 0, "DMF", 400)

""" 
-------------------------------------------------------------------------
Experiment A1
-------------------------------------------------------------------------
"""
# Begin by homing the mill
mill.home()

""" Pipette solution #N1"""
Target_vial = Solution1.coordinates
Target_well = plate.get_coordinates("A1")

#move_pipette_to_position(Target_vial['x'],Target_vial['y'],Target_vial['z'])
#withdraw(0.140, Target_vial, withdrawl_height, 0.4,pump)
withdraw(0.140, Solution1.coordinates, Solution1.depth, 0.4,pump)
purge(0.020, purge_vial.coordinates, -30, 0.4, pump)
#move_pipette_to_position(Target_vial['x'],Target_vial['y'],Target_vial['z'])
infuse(0.10, Target_well, withdrawl_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -30, 0.4, pump)
print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
mill.home()

""" 
Electrode - chronoamperometry
-------------------------------------------------------------------------
"""
move_electrode_to_position(Target_well)
# Initiate pstat experiment
#pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
mill.home()


""" 
Remove Solution 1 deposition
-------------------------------------------------------------------------
"""
#move_pipette_to_position(Target_well)
withdraw(0.100, Target_well, -36, 0.4, pump)
infuse(0.120, purge_vial, withdrawl_height, 0.4, pump)
mill.home()

""" 
Pipette - Dimethylferrocene solution
-------------------------------------------------------------------------
"""
#move_pipette_to_position(DMF.coordinates)
withdraw(0.140, DMF.coordinates, withdrawl_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -30, 0.4, pump)
#move_pipette_to_position(plate.get_coordinates("A1"))
infuse(0.100,Target_well, infuse_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -30, 0.4, pump)
mill.home()

"""
Electrode - Cyclic voltammetry
-------------------------------------------------------------------------
"""
move_electrode_to_position(plate.get_coordinates("A1"))
# Initiate pstat experiment
#pstatcontrol.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
mill.home()

"""
Remove Remove DMF solution
-------------------------------------------------------------------------
"""
withdraw(0.120, Target_well, plate.depth("A1"), 0.4, pump)
infuse(0.140, purge_vial, withdrawl_height, 0.4, pump)
#infuse(0.140, purge_vial, purge_vial.depth, 0.4, pump)
mill.home()
