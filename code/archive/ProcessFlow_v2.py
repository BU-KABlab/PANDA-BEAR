import time
import nesp_lib
import serial
from code.archive.classes import Vial, Wells, MillControl
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


def withdraw(volume: float, position: list, height: float, rate: float, ser_pump):
    """Set the pump direction to withdraw the given volume at the given rate and height.
    volume <float> (ml) | rate <float> (ml/m) | height <float> <mm>
    """
    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position["x"], position["y"], position["z"])
    mill.current_status()
    move_pipette_to_position(position["x"], position["y"], position["z"] + height)
    mill.current_status()
    # Perform the withdrawl
    if ser_pump.volume_withdrawn + volume >= 0.2:
        raise Exception("The command will overfill the pipette. Not running")
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
    move_pipette_to_position(position["x"], position["y"], position["z"])
    mill.current_status()
    return 0


def infuse(volume: float, position: list, height: float, rate: float, pump):
    """Set the pump direction to infuse the given volume at the given rate.
    volume <float> (ml) | rate <float> (ml/m)
    """
    move_pipette_to_position(position["x"], position["y"], position["z"])
    mill.current_status()
                             
    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position["x"], position["y"], position["z"] + height)
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
    move_pipette_to_position(position["x"], position["y"], position["z"])
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
    command = mill_move.format(x - 80, y, z)  # pipette offset
    response = mill.execute_command(str(command))
    return response


def move_electrode_to_position(x,y,z):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x + 78, y, z)  # electrode offset
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
purge_vial = Vial(-10,-50,0,-80,'waste',0)
#purge = infuse(20, purge_vial.coordinates, -30, 0.4, pump)
purge = infuse
# Common values
vial_withdraw_height = -80
well_withdraw_height = -78
well_infuse_height = -76
vial_infuse_height = vial_withdraw_height

# Set up wells
plate = Wells(-230, -75, 0)

# Define locations of vials and their contents
#Sol1 = Vial(-10, -50, 0, -80, "water", 400)
Sol2 = Vial(-10, -84, 0, -80, "water", 400)
Sol3 = Vial(-10, -115, 0, -80, "water", 400)
Sol4 = Vial(-10, -150, 0, -80, "water", 400)
Sol5 = Vial(-10, -182, 0, -80, "water", 400)

""" 
-------------------------------------------------------------------------
Experiment A1
-------------------------------------------------------------------------
"""
# Begin by homing the mill
mill.home()
time.sleep(20)

# Pipette solution #N1
Target_vial = Sol2.coordinates
Target_vial2 = Sol5.coordinates
purge_coord = purge_vial.coordinates
Target_well = plate.get_coordinates("A1")

#move_pipette_to_position(Target_vial['x'],Target_vial['y'],Target_vial['z'])
withdraw(0.140, Target_vial, vial_withdraw_height, 0.4,pump)
purge(0.020, purge_vial.coordinates, -80, 0.4, pump)
#move_pipette_to_position(Target_vial['x'],Target_vial['y'],Target_vial['z'])
infuse(0.10, Target_well, well_infuse_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -80, 0.4, pump)
print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
mill.home()

# Electrode - chronoamperometry
move_electrode_to_position(Target_well['x'],Target_well['y'],Target_well['z'])
print("electrode in position")
# Initiate pstat experiment
#pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
time.sleep(20) #adding sleep step in place of pstat experiment for testing
mill.home()
'''
# Remove Solution 1 deposition
move_pipette_to_position(Target_well['x'],Target_well['y'],Target_well['z'])
withdraw(0.100, Target_well, -40, 0.4, pump)
infuse(0.120, purge_vial, well_infuse_height, 0.4, pump)
mill.home()

#Pipette - Dimethylferrocene solution
move_pipette_to_position(Target_vial2['x'],Target_vial2['y'],Target_vial2['z'])
withdraw(0.140, Sol5, vial_withdraw_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -40, 0.4, pump)
move_pipette_to_position(plate.get_coordinates("A1"))
infuse(0.100,Target_well, well_infuse_height, 0.4, pump)
purge(0.020, purge_vial.coordinates, -40, 0.4, pump)
mill.home()

# Electrode - Cyclic voltammetry
move_electrode_to_position(plate.get_coordinates("A1"))
# Initiate pstat experiment
#pstatcontrol.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
mill.home()

# Remove Remove DMF solution
move_pipette_to_position(Target_well['x'],Target_well['y'],Target_well['z'])
withdraw(0.120, Target_well, well_withdraw_height, 0.4, pump)
infuse(0.140, purge_vial, vial_infuse_height, 0.4, pump)
mill.home()
'''