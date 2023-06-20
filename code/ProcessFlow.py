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
    # move_pipette_to_position(
    #     position["x"], position["y"], 0
    # )  # start above the location

    move_pipette_to_position(
        position["x"], position["y"], position["z"]
    )  # go to the top

    move_pipette_to_position(
        position["x"], position["y"], depth
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


def infuse(volume: float, position: dict, depth: float, rate: float, ser_pump: object):
    """
    Infuse the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be infused in milliliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to lower from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    # move_pipette_to_position(
    #     position["x"], position["y"], 0
    # )  # first move to the x,y coord

    move_pipette_to_position(
        position["x"], position["y"], position["z"]
    )  # then lower to the top

    move_pipette_to_position(
        position["x"], position["y"], depth
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
        x - 88, y, z
    )  # x-coordinate has 84 mm offset for pipette location
    response = mill.execute_command(str(command))
    return response


def move_electrode_to_position(coordinates: dict):
    """
    Move the electrode to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        coordinates["x"] + 82, coordinates["y"] + 1, 0
    )  # electrode has 84.5 mm offset
    response = mill.execute_command(str(command))
    # TODO: create seperate raise and lower electrode functions 
   
    command = mill_move.format(
        coordinates["x"] + 82, coordinates["y"] + 1, coordinates["z"]
    )  # electrode has 84.5 mm offset
    response = mill.execute_command(str(command))
    time.sleep(15)
    command = mill_move.format(
        coordinates["x"] + 82, coordinates["y"] + 1, 0
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
purge_vial = Vial(0,-50,0,-80,'waste',0) # TODO replace heigh with real height

# Common values
vial_withdraw_height = -80
vial_infuse_height = vial_withdraw_height

well_withdraw_height = -101
well_infuse_height = -98

pumping_rate = 0.4

# Set up wells
plate = Wells(-219, -76, 0)

# Define locations of vials and their contents
#Sol1 = Vial(-10, -50, 0, -80, "water", 400)
Sol2 = Vial( 0,  -84, 0, -80, "water", 400)
Sol3 = Vial( 0, -115, 0, -80, "water", 400)
Sol4 = Vial( 0, -150, 0, -80, "water", 400)
Sol5 = Vial( 0, -182, 0, -80, "water", 400)

""" 
-------------------------------------------------------------------------
Experiment A1
-------------------------------------------------------------------------
"""
mill.home() 

""" 
Pipette solution 1 into C1
-------------------------------------------------------------------------
"""
# Pipette solution #N1
#Target_vial = Sol2.coordinates
#Target_vial2 = Sol5.coordinates
purge_coord = purge_vial.coordinates
Target_well = plate.get_coordinates("D5")

withdraw(0.140, Sol2.coordinates, vial_withdraw_height, pumping_rate, pump)
purge(0.020, purge_vial.position, vial_infuse_height)
infuse(0.100, Target_well, well_infuse_height, pumping_rate, pump)
purge(0.020, purge_vial.position, vial_infuse_height)
print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
#mill.home()

""" 
Electrode - chronoamperometry
-------------------------------------------------------------------------
"""
electrode_move_to = {'x':Target_well['x'],'y':Target_well['y'],'z':plate.depth('A1')}
move_electrode_to_position(electrode_move_to)
# Initiate pstat experiment
# pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
#mill.home()


""" 
Remove Solution 1 deposition
-------------------------------------------------------------------------
"""
# move_pipette_to_position(Target_well)
withdraw(0.140, Target_well, well_withdraw_height, pumping_rate, pump)
purge(0.140, purge_vial.position, vial_infuse_height)
#mill.home()

# """ 
# Pipette - Dimethylferrocene solution
# -------------------------------------------------------------------------
# """
# # move_pipette_to_position(DMF_vial.coordinates)
# withdraw(0.140, DMF_vial.coordinates, withdrawl_height, pumping_rate, pump)
# purge(0.020, purge_vial.coordinates, purge_vial.depth, pumping_rate, pump)
# # move_pipette_to_position(wells_plate.get_coordinates("A1"))
# infuse(0.100, Target_well, infuse_height, pumping_rate, pump)
# purge(0.020, purge_vial.coordinates, purge_vial.depth, pumping_rate, pump)
# mill.home()

# """
# Electrode - Cyclic voltammetry
# -------------------------------------------------------------------------
# """
# move_electrode_to_position(wells_plate.get_coordinates("A1"))
# # Initiate pstat experiment
# # pstatcontrol.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
# mill.home()

# """
# Remove Remove DMF_vial solution
# -------------------------------------------------------------------------
# """
# withdraw(0.120, Target_well, wells_plate.depth("A1"), pumping_rate, pump)
# infuse(0.120, purge_vial, withdrawl_height, pumping_rate, pump)
# # infuse(0.140, purge_vial, purge_vial.depth, 0.4, pump)
# mill.home()

mill.__exit__()