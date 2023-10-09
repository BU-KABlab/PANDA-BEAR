import time
import nesp_lib
from code.archive.classes import Vial, MillControl, Wells
from generate_instructions import instruction_reader
import sys

# HQ potentiostat#
# import demo.pstatcontrol

# Constants
vial_withdraw_height = -80
vial_infuse_height = vial_withdraw_height

well_withdraw_height = -101
well_infuse_height = -98
pumping_rate = 0.4


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


def withdraw(volume: float, rate: float, ser_pump: object):
    """
    Withdraw the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be withdrawn in milliliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to plunge from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
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
        print('Withdrawing...')
        while ser_pump.running:
            pass
        print('Done withdrawing')
        time.sleep(2)

        print(f"Pump has withdrawn: {ser_pump.volume_withdrawn} ml")
    #vessel.update_volume(-volume)

    return 0


def infuse(volume: float, rate: float, ser_pump: object):
    """
    Infuse the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be infused in milliliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to lower from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    # then lower to the pipetting depth
    #move_pipette_to_position(position["x"], position["y"], depth)
    # Perform infusion
    ser_pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    ser_pump.pumping_volume = (
        volume  # Sets the pumping volume of the pump in units of milliliters.
    )
    ser_pump.pumping_rate = (
        rate  # Sets the pumping rate of the pump in units of milliliters per minute.
    )
    ser_pump.run()
    print('Infusing...')
    while ser_pump.running:
        pass
    print('Done infusing')
    time.sleep(2)
    # TODO update the volume with the infusion step vessel.update_volume(volume)
    print(f"Pump has infused: {ser_pump.volume_infused} ml")

    return 0


def move_center_to_position(x,y,z):
    """
    Move the mill to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {
        'x': 0,
        'y': 0,
        'z': 0
    }

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(command)
    return 0


def move_pipette_to_position(x, y, z = 0.00):
    """
    Move the pipette to the specified coordinates.
    Args:
        x (float): X coordinate.
        y (float): Y coordinate.
        z (float): Z coordinate.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {
        'x': -88,
        'y': 1,
        'z': 0
    }

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        x + offsets['x'], 
        y + offsets['y'], 
        z + offsets['z']
    )  # x-coordinate has 84 mm offset for pipette location
    mill.execute_command(str(command))
    return 0


def move_electrode_to_position(x,y,z):
    """
    Move the electrode to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {
        'x': 82,
        'y': 1,
        'z': 0
    }
    # move to specified coordinates
    mill_move = "G0 X{} Y{} Z{}"  
    command = mill_move.format(
        x + offsets['x'], 
        y + offsets['y'], 
        z + offsets['z']
        ) 
    mill.execute_command(str(command))
    return 0

def purge(purge_vial: Vial,purge_volume = 0.02):
    """
    Perform purging from the pipette.
    Args:
        volume (float): Volume to be purged in milliliters. Default is 0.02 ml.
        purge_vial_location (dict): Dictionary containing x, y, and z coordinates of the purge vial.
        purge_vial_depth (float): Depth to lower from the purge vial position in millimeters. Default is 0.00 mm.
    """
    infuse(purge_volume,pumping_rate, pump)
    purge_vial.update_volume(purge_volume)
    print(f'Purge vial new volume: {purge_vial.volume}')

def electrode(location: dict, depth, test,test_duration = 10):
  
    x = location['x'] 
    y = location['y'] 
    z = location['z']
    
    print('Moving electrode to test well...')
    print(f'{x, y, z}')
    move_electrode_to_position(x, y, 0) # Move to z=0 above the location
    move_electrode_to_position(x,y,depth) # move in the z-direction
    time.sleep(test_duration) # stay there for the duration of the test
    move_electrode_to_position(x,y,0) # Move back to z=0 above the location

def pipette(volume: float, solution: Vial, target_well: str, purge_volume = 0.020):
    """
    Perform the full pipetting sequence
    Args:
        volume (float): Volume to be pipetted into desired well
        solution (Vial object): the vial source or solution to be pipetted
        target_well (str): The alphanumeric name of the well you would like to pipette into
        purge_volume (float): Desired about to purge before and after pipetting
    """
    ## First half: pick up solution
    print('Withdrawing solution...')
    move_pipette_to_position(solution.coordinates['x'], solution.coordinates['y'], 0) # start at safe height
    move_pipette_to_position(solution.coordinates['x'], solution.coordinates['y'], solution.coordinates['z']) # go to object top
    move_pipette_to_position(solution.coordinates['x'], solution.coordinates['y'], solution.depth) # go to soltuion depth
    withdraw(volume + 2 * purge_volume, pumping_rate, pump)
    solution.update_volume(-volume + 2 * purge_volume)
    print(f'{solution} new volume: {solution.volume}')
    move_pipette_to_position(solution.coordinates['x'],solution.coordinates['y'],0) # return to safe height

    ## Intermediate: Purge
    print('Purging...')
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.coordinates['z'])
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
    purge(PurgeVial, purge_volume)
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
    
    ## Second Half: Deposit to well
    print('Depositing into well...')
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # start at safe height
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],wellplate.get_coordinates(target_well)['z']) # go to object top
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],wellplate.depth(target_well)) # go to solution depth
    infuse(volume, pumping_rate, pump)
    wellplate.update_volume(target_well,volume)
    print(f'Well {target_well} volume: {wellplate.volume(target_well)}')
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # return to safe height
    
    ## Intermediate: Purge
    print('Purging...')
    move_pipette_to_position(PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
    move_pipette_to_position(PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], PurgeVial.coordinates['z'])
    move_pipette_to_position(PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], PurgeVial.depth)
    purge(PurgeVial, purge_volume)
    move_pipette_to_position(PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
    
    print(f"Remaining volume in pipette: {pump.volume_withdrawn}")

def clear_well(volume: float, target_well: str):
    """
    Perform the full pipetting sequence
    Args:
        volume (float): Volume to be pipetted into desired well
        solution (Vial object): the vial source or solution to be pipetted
        target_well (str): The alphanumeric name of the well you would like to pipette into
        purge_volume (float): Desired about to purge before and after pipetting
    """
    print('Clearing well ',target_well)
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'],       0) # start at safe height
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'],  wellplate.get_coordinates(target_well)['z']) # go to object top
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'],       wellplate.depth(target_well)) # go to solution depth
    
    withdraw(volume + 0.02, pumping_rate, pump) # TODO break into 4 parts where we withdraw from each corner
    wellplate.update_volume(target_well,-volume)
    
    print(f'Well {target_well} volume: {wellplate.volume(target_well)}')
    move_pipette_to_position(wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'],       0) # return to safe height
    
    print('Moving to purge vial...')
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.coordinates['z'])
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
    print('Purging...')
    purge(PurgeVial, volume + 0.02)
    move_pipette_to_position(PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
    
    print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
    
## Program Set Up
mill = MillControl()
#mill.home() 
pump = set_up_pump()
PurgeVial = Vial(0,-50,'waste',1)

# Set up wells
wellplate = Wells(-219, -76, 0)

# Define locations of vials and their contents
#Sol0 = PurgeVial
Sol1 = Vial( 0,  -84, "water", 20)
Sol2 = Vial( 0, -115, "water", 20)
Sol3 = Vial( 0, -150, "water", 20)
Sol4 = Vial( 0, -182, "water", 20)

## Set up experiments
experiements= [
    {'Target Well':  'A4','Solution': Sol1,'Pipette Volume': 0.1,'Test Type': 'Test','Test duration': 10},
    {'Target Well':  'B6','Solution': Sol1,'Pipette Volume': 0.1,'Test Type': 'Test','Test duration': 10},
    {'Target Well':  'D7','Solution': Sol1,'Pipette Volume': 0.1,'Test Type': 'Test','Test duration': 10},
    {'Target Well':  'D9','Solution': Sol1,'Pipette Volume': 0.1,'Test Type': 'Test','Test duration': 10},
    {'Target Well': 'H12','Solution': Sol1,'Pipette Volume': 0.1,'Test Type': 'Test','Test duration': 10},
    ]

## Run the experiments
for run in experiements:

    try:
        ## Pipette solution 1 into target well
        pipette(run['Pipette Volume'],run['Solution'],run['Target Well'])
        #print(f"Remaining volume in pipette: {pump.volume_withdrawn}")

        ## Electrode - chronoamperometry
        electrode(wellplate.get_coordinates(run['Target Well']),wellplate.depth(run['Target Well']), 'test',run['Test duration'])
        # Initiate pstat experiment
        # pstatcontrol.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)

        ## Remove Solution 1 deposition
        clear_well(0.1,run['Target Well'])


    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print('Exception: ',e)
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)
        
        
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