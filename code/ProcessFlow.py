import time
import nesp_lib
from demo.classes import Vial, Wells, MillControl as mill
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
    return pump


def withdraw(volume: float, position: list, height: float, rate: float, ser_pump):
    """Set the pump direction to withdraw the given volume at the given rate and height.
    volume <float> (ml) | rate <float> (ml/m) | height <float> <mm>
    """
    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position(1), position(2), position(3) + height)

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
    move_pipette_to_position(position(1), position(2), position(3))
    return 0


def infuse(volume: float, position: list, height: float, rate: float, pump):
    """Set the pump direction to infuse the given volume at the given rate.
    volume <float> (ml) | rate <float> (ml/m)
    """

    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position(1), position(2), position(3) + height)

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

    # Move the pipette down to the given height at the current position
    move_pipette_to_position(position(1), position(2), position(3) + height)
    return 0


def move_center_to_position(coordinates: list):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(coordinates(0), coordinates(1), coordinates(2))
    response = mill.send_to_mill(command)
    return response


def move_pipette_to_position(coordinates: list):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        coordinates(0) - 45, coordinates(1), coordinates(2)
    )  # x-coordinate has 45 mm offset for pipette location
    response = mill.send_to_mill(command)
    return response


def move_electrode_to_position(coordinates: list):
    """
    INPUT: x, y, z coordinates as int or float to where you want the mill to move absolutely.
    """
    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        coordinates(0) + 45, coordinates(1), coordinates(2)
    )  # electrode has 45 mm offset
    response = mill.send_to_mill(command)
    return response


""" 
-------------------------------------------------------------------------
Program Set Up
-------------------------------------------------------------------------
"""
# Set up the pump
pump = set_up_pump()
# Define the amount to purge, vial location, height,and rate to purge
purge_vial = Vial(-20,-100,-10,-26,'purge',0)
purge = infuse(20, purge_vial.coordinates, -30, 0.4, pump)

# Common values
withdrawl_height = -30
infuse_height = withdrawl_height

# Set up wells
Wells(-150, -10, 0)

# Define locations of vials and their contents
Solution1 = Vial(0, 0, 0, -36, "water", 400)
DMF = Vial(0, -10, 0 , -36, "DMF", 400)

""" 
-------------------------------------------------------------------------
Experiment A1
-------------------------------------------------------------------------
"""
# Begin by homing the mill
mill.home()


# Pipette solution #N1
Target_vial = Solution1.coordinates
Target_well = Wells.get_coordinates("A1")
move_pipette_to_position(Target_vial)
withdraw(140, Target_vial, withdrawl_height, (0.4).pump)
purge
move_pipette_to_position(Target_well)
infuse(0.10, Target_well, withdrawl_height, 0.4, pump)
purge
print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
mill.home()

# Electrode - chronoamperometry
move_electrode_to_position(Target_well)
# Initiate pstat experiment
#pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
mill.home()

# Remove Solution 1 deposition
move_pipette_to_position(Target_well)
withdraw(100, Target_well, -36, 0.4, pump)
infuse(120, purge_vial, withdrawl_height, 0.4, pump)
mill.home()

#Pipette - Dimethylferrocene solution
move_pipette_to_position(DMF.coordinates)
withdraw(140, DMF.coordinates, withdrawl_height, 0.4, pump)
purge
move_pipette_to_position(Wells.get_coordinates("A1"))
infuse(100,Target_well, infuse_height, 0.4, pump)
purge
mill.home()

# Electrode - Cyclic voltammetry
move_electrode_to_position(Wells.get_coordinates("A1"))
# Initiate pstat experiment
#pstatcontrol.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
mill.home()

# Remove Remove DMF solution
move_pipette_to_position(Target_well)
withdraw(120, Target_well, -36, 0.4, pump)
infuse(140, purge_vial, withdrawl_height, 0.4, pump)
mill.home()
