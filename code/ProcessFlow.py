import time
import nesp_lib
import serial
from classes import Vial, Wells, MillControl

# HQ potentiostat#
# import demo.pstatcontrol


def set_up_pump():
    """
    Set up the WPI syringe pump.
    Returns:
        Pump: Initialized pump object.
    """
    pump_port = nesp_lib.Port("COM5", 19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699  # millimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f"Pump at address: {pump.address}")
    time.sleep(2)
    return pump

def set_up_mill():
    """
    Set up the CNC mill.
    Returns:
        serial.Serial: Initialized serial object for mill communication.
    """
    mill_serial = serial.Serial(
        port="COM4",
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
    )
    time.sleep(2)
    return mill_serial


def withdraw(volume: float, position: list, depth: float, rate: float, ser_pump: object):
    """
    Withdraw the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be withdrawn in milliliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to plunge from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    # Move the pipette down to the given height at the current position
    move_pipette_to_position(
        position["x"], position["y"], 0
    )  # start above the location

    move_pipette_to_position(
        position["x"], position["y"], position["z"]
    )  # go to the top

    move_pipette_to_position(
        position["x"], position["y"], position["z"] + depth
    )  # plunge a calculated depth

    # Perform the withdrawl
    if ser_pump.volume_withdrawn + volume >= 0.2:
        raise Exception("The command will overfill the pipette. Stopping run")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        ser_pump.pumping_volume = (
            volume  # Sets the pumping volume of the pump in units of milliliters.
        )
        ser_pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.run()
        while ser_pump.running:
            pass
        time.sleep(2)
        print(f"Pump has withdrawn: {ser_pump.volume_withdrawn} ml")

    # Return to safe height
    move_pipette_to_position(position["x"], position["y"], 0)

    return 0


def infuse(volume: float, position: list, depth: float, rate: float, ser_pump: object):
    """
    Infuse the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be infused in milliliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to lower from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    move_pipette_to_position(
        position["x"], position["y"], 0
    )  # first move to the x,y coord

    move_pipette_to_position(
        position["x"], position["y"], position["z"]
    )  # then lower to the top

    move_pipette_to_position(
        position["x"], position["y"], position["z"] + depth
    )  # then lower to the pipetting depth

    # Perform infusion
    ser_pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    ser_pump.pumping_volume = (
        volume  # Sets the pumping volume of the pump in units of milliliters.
    )
    ser_pump.pumping_rate = (
        rate  # Sets the pumping rate of the pump in units of milliliters per minute.
    )
    ser_pump.run()
    while ser_pump.running:
        pass
    time.sleep(2)
    print(f"Pump has infused: {ser_pump.volume_infused} ml")

    move_pipette_to_position(
        position["x"], position["y"], 0
    )  # Move the pipette back up

    return 0


def move_center_to_position(coordinates: list):
    """
    Move the mill to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(coordinates["x"], coordinates["y"], coordinates["z"])
    response = mill.execute_command(command)
    return response


def move_pipette_to_position(x, y, z):
    """
    Move the pipette to the specified coordinates.
    Args:
        x (float): X coordinate.
        y (float): Y coordinate.
        z (float): Z coordinate.
    Returns:
        str: Response from the mill after executing the command.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        x - 84, y, z
    )  # x-coordinate has 84 mm offset for pipette location
    response = mill.execute_command(str(command))
    return response


def move_electrode_to_position(coordinates: list):
    """
    Move the electrode to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        coordinates["x"] + 84.5, coordinates["y"], coordinates["z"]
    )  # electrode has 84.5 mm offset
    response = mill.execute_command(str(command))
    return response

def purge(volume = 0.02, purge_vial_location = {'x':0,'y':0,'z':0}, purge_vial_depth = 0.00):
    """
    Perform purging from the pipette.
    Args:
        volume (float): Volume to be purged in milliliters. Default is 0.02 ml.
        purge_vial_location (dict): Dictionary containing x, y, and z coordinates of the purge vial.
        purge_vial_depth (float): Depth to lower from the purge vial position in millimeters. Default is 0.00 mm.
    """
    infuse(volume, purge_vial_location, purge_vial_depth, 0.4, pump)

""" 
-------------------------------------------------------------------------
Program Set Up
-------------------------------------------------------------------------
"""

mill = MillControl(set_up_mill())
pump = set_up_pump()
purge_vial = Vial(0, -200, 0, 0, "waste", 0) # TODO replace heigh with real height

# Common values
# TODO eliminate these height values by calculating the volume/depth for each vessel based on their z-top and bottom
withdrawl_height = -30 # depth to lower to for withdrawl
infuse_height = withdrawl_height
purge_volume = 0.02 #ml
pumping_rate = 0.4 # max of 0.6 ml/min

# Set up wells
wells_plate = Wells(-200, -100, 0)
# TODO floor-of-well = -##

# Set up vials
solution_1_vial = Vial(0, -100, 0, -36, "water", 400) # Define locations of vials and their contents
purge_vial = Vial(0, -200, 0, -36, "waste", 0) # Define the amount to purge, vial location, height,and rate to purge
DMF_vial = Vial(0, -150, 0, -36, "DMF", 400)

""" 
-------------------------------------------------------------------------
Experiment A1
-------------------------------------------------------------------------
"""
mill.home() 

""" 
Pipette solution 1 into A1
-------------------------------------------------------------------------
"""
Target_well = wells_plate.get_coordinates("A1")

withdraw(0.140, solution_1_vial.coordinates, solution_1_vial.depth, pumping_rate, pump)
purge(purge_volume,purge_vial.position,purge_vial.depth)
infuse(0.100, Target_well, infuse_height, pumping_rate, pump)
purge(purge_volume,purge_vial.position,purge_vial.depth)
print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
mill.home()

""" 
Electrode - chronoamperometry
-------------------------------------------------------------------------
"""
move_electrode_to_position(Target_well)
# Initiate pstat experiment
# pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
mill.home()


""" 
Remove Solution 1 deposition
-------------------------------------------------------------------------
"""
# move_pipette_to_position(Target_well)
withdraw(0.120, Target_well, withdraw_height, pumping_rate, pump)
infuse(0.120, purge_vial, infuse_height, pumping_rate, pump)
mill.home()

""" 
Pipette - Dimethylferrocene solution
-------------------------------------------------------------------------
"""
# move_pipette_to_position(DMF_vial.coordinates)
withdraw(0.140, DMF_vial.coordinates, withdrawl_height, pumping_rate, pump)
purge(0.020, purge_vial.coordinates, purge_vial.depth, pumping_rate, pump)
# move_pipette_to_position(wells_plate.get_coordinates("A1"))
infuse(0.100, Target_well, infuse_height, pumping_rate, pump)
purge(0.020, purge_vial.coordinates, purge_vial.depth, pumping_rate, pump)
mill.home()

"""
Electrode - Cyclic voltammetry
-------------------------------------------------------------------------
"""
move_electrode_to_position(wells_plate.get_coordinates("A1"))
# Initiate pstat experiment
# pstatcontrol.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
mill.home()

"""
Remove Remove DMF_vial solution
-------------------------------------------------------------------------
"""
withdraw(0.120, Target_well, wells_plate.depth("A1"), pumping_rate, pump)
infuse(0.120, purge_vial, withdrawl_height, pumping_rate, pump)
# infuse(0.140, purge_vial, purge_vial.depth, 0.4, pump)
mill.home()
