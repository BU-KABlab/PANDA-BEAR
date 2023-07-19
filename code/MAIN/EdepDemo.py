import time, nesp_lib, serial, sys
from classes import Vial, MillControl, Wells
from generate_instructions import instruction_reader
import gamrycontrol as echem
import os.path
import datetime
import comtypes
import comtypes.client as client

def verbose_output(*args):
    pass


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
    print(f"\tPump at address: {pump.address}")
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
        print('\tWithdrawing...')
        while ser_pump.running:
            pass
        print('\tDone withdrawing')
        time.sleep(2)

        print(f"\tPump has withdrawn: {ser_pump.volume_withdrawn} ml")
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
    if volume > 0.0:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
        ser_pump.pumping_volume = (
            volume  # Sets the pumping volume of the pump in units of milliliters.
        )
        ser_pump.pumping_rate = (
            rate  # Sets the pumping rate of the pump in units of milliliters per minute.
        )
        ser_pump.run()
        print('\tInfusing...')
        while ser_pump.running:
            pass
        print('\tDone infusing')
        time.sleep(1)
        print(f"\tPump has infused: {ser_pump.volume_infused} ml")
    else:
        pass
    return 0


def move_center_to_position(mill:object, x,y,z):
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

    mill_move = "G1 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(command)
    return 0


def move_pipette_to_position(mill:object, x, y, z = 0.00, ):
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
        'x': -86,
        'y': 0,
        'z': 0
    }

    mill_move = "G1 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        x + offsets['x'], 
        y + offsets['y'], 
        z + offsets['z']
    )  # x-coordinate has 84 mm offset for pipette location
    mill.execute_command(str(command))
    return 0


def move_electrode_to_position(mill: object, x,y,z):
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
    mill_move = "G1 X{} Y{} Z{}"  
    command = mill_move.format(
        x + offsets['x'], 
        y + offsets['y'], 
        z + offsets['z']
        ) 
    mill.execute_command(str(command))
    return 0

def purge(purge_vial: Vial,pump: object, purge_volume = 0.02, pumping_rate = 0.4):
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

def electrode(mill: object, location: dict, depth, test,test_duration = 10):
  
    x = location['x'] 
    y = location['y'] 
    z = location['z']
    
    print('Moving electrode to test well...')
    print(f'{x, y, z}')
    move_electrode_to_position(mill, x, y, 0) # Move to z=0 above the location
    move_electrode_to_position(mill, x,y,depth) # move in the z-direction
    time.sleep(test_duration) # stay there for the duration of the test
    move_electrode_to_position(mill, x,y,0) # Move back to z=0 above the location

def pipette(volume: float, solution: Vial, target_well: str, pumping_rate, PurgeVial: object, wellplate: Wells, pump: object, mill: object, purge_volume = 0.020):
    """
    Perform the full pipetting sequence
    Args:
        volume (float): Volume to be pipetted into desired well
        solution (Vial object): the vial source or solution to be pipetted
        target_well (str): The alphanumeric name of the well you would like to pipette into
        purge_volume (float): Desired about to purge before and after pipetting
    """
    if volume > 0.00:
        ## First half: pick up solution
        print('Withdrawing solution...')
        move_pipette_to_position(mill, solution.coordinates['x'], solution.coordinates['y'], 0) # start at safe height
        move_pipette_to_position(mill, solution.coordinates['x'], solution.coordinates['y'], solution.depth) # go to soltuion depth
        
        withdraw(volume + 2 * purge_volume, pumping_rate, pump)
        solution.update_volume(-(volume + 2 * purge_volume))
        print(f'{solution.name} new volume: {solution.volume}')
        move_pipette_to_position(mill, solution.coordinates['x'],solution.coordinates['y'],0) # return to safe height
    
        ## Intermediate: Purge
        print('Purging...')
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
        purge(PurgeVial, pump, purge_volume)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        
        ## Second Half: Deposit to well
        print('Depositing into well...')
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # start at safe height
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],wellplate.depth(target_well)) # go to solution depth
        infuse(volume, pumping_rate, pump)
        wellplate.update_volume(target_well,volume)
        print(f'Well {target_well} volume: {wellplate.volume(target_well)}')
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # return to safe height
        
        ## Intermediate: Purge
        print('Purging...')
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], PurgeVial.depth)
        purge(PurgeVial, pump, purge_volume)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
        
        print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
    else:
        pass

def clear_well(volume: float, target_well: str, wellplate: object, pumping_rate, pump: object, PurgeVial: Vial, mill: object):
    import math
    repititions = math.ceil(volume/0.200)
    repition_vol = volume/repititions
    
    for j in range(repititions):
        print('Clearing well ',target_well)
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], 0) # start at safe height
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z']) # go to object top
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.depth(target_well)) # go to solution depth
        withdraw(repition_vol + 0.02, pumping_rate, pump)
        wellplate.update_volume(target_well,-volume)
        
        print(f'Well {target_well} volume: {wellplate.volume(target_well)}')
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], 0) # return to safe height
        
        print('Moving to purge vial...')
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.coordinates['z'])
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
        print('Purging...')
        purge(PurgeVial, pump, repition_vol + 0.02)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        
        print(f"Remaining volume in well: {wellplate.volume(target_well)}")


def main():
    # Constants
    #vial_withdraw_height = -80
    #vial_infuse_height = vial_withdraw_height
    
    #well_withdraw_height = -101
    #well_infuse_height = -98
    pumping_rate = 0.5
    Well_Rows = 'ABCDEFGH'
    Well_Columns = 13
    
        
    ## Program Set Up
    print('Beginning protocol:\nConnecting to Mill and Pump:')
    mill = MillControl()
    #mill.home() 
    pump = set_up_pump()
    PurgeVial = Vial(-2,-50,'waste',1.00)
    
    ## Set up wells
    wellplate = Wells(-218, -74, 0.00)
    
    ## Define locations of vials and their contents
    #Sol0 = PurgeVial
    Sol1 = Vial( -2,  -80, "Acetonitrile", 20.0, name = 'ACN')
    Sol2 = Vial( -2, -110, "PEG", 20.0, name = 'PEG')
    Sol3 = Vial( -2, -140, "Acrylate", 20.0, name = 'Acrylate')
    Sol4 = Vial( -2, -170, "DMF", 20.0, name = 'DMF')
    
    ## Set up experiments
    
    color1 = instruction_reader('sol1.csv', Sol1, Well_Rows, Well_Columns)
    color2 = instruction_reader('sol2.csv', Sol2, Well_Rows, Well_Columns)
    dilution = instruction_reader('sol3.csv', Sol3, Well_Rows, Well_Columns)
    water_layer = instruction_reader('water.csv', Sol3, Well_Rows, Well_Columns)
    experiments = [color1, color2, dilution, water_layer]
    experiments = [color1]
    ## Run the experiments
    try:
        #for i in len(color1): #loop per well
        for i in range(len(color1)): #loop per well
            total_well_volume = 0
            
            ## Deposit all experiment solutions into well
            for solution in experiments:
                    print(f"\npipetting {solution[i]['Pipette Volume']} ul from {solution[i]['Solution'].name}: {solution[i]['Solution'].contents} into well {solution[i]['Target Well']}")
                    pipette(float(solution[i]['Pipette Volume'])/1000,solution[i]['Solution'],solution[i]['Target Well'],pumping_rate, PurgeVial, wellplate, pump, mill)
                    total_well_volume += (solution[i]['Pipette Volume'])/1000
                    
                    solution_volume = (solution[i]['Pipette Volume'])/1000 #1000 because the demo is in ml
                    
                    ## Beginning of pipette flushing procedure
                    print('\n\nMoving to flush with Sol3...')
                    move_pipette_to_position(mill, Sol1.coordinates['x'], Sol1.coordinates['y'], 0)
                    move_pipette_to_position(mill, Sol1.coordinates['x'], Sol1.coordinates['y'], Sol3.depth)
                    print('\tWithdrawing Sol3...')
                    withdraw(solution_volume + 0.02, 0.5, pump)
                    move_pipette_to_position(mill, Sol1.coordinates['x'], Sol1.coordinates['y'], 0)
                    
                    print('\tMoving to purge...')
                    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
                    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
                    print('\tPurging...')
                    purge(PurgeVial, pump, solution_volume + 0.02)
                    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
                    ## End of pipette flushing procedure
            target_well = solution[i]['Target Well']
            ## set the name of the files for the echem experiments
            echem.pstatcontrol.setfilename(target_well, 'dep')
            ## echem CA - deposition
            move_electrode_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z'])
            echem.exp.CA(echem.CAvi, echem.CAti, echem.CAv1, echem.CAt1, echem.CAv2, echem.CAt2, echem.CAsamplerate) #CA
            while active == True:
                client.PumpEvents(1)
                time.sleep(0.1)
            ## echem plot the data
            echem.pstatcontrol.plotdata(echem.CA)
            
            ## Withdraw all well volume            
            if wellplate.volume(target_well) != total_well_volume:
                print(f'Well volume: {wellplate.volume(target_well)} != Running total: {total_well_volume}')
                wait = input("Press Enter to continue.")
            clear_well(wellplate.volume(target_well), target_well, wellplate, pumping_rate, pump, PurgeVial, mill)
            #clear_well(total_well_volume, target_well, wellplate, pumping_rate, pump, PurgeVial, mill)
            
                     
            ## Rinse the well 3x
            for i in range(3):
                rinse_vol = 0.180 #ml
                pipette(rinse_vol, Sol1, target_well, pumping_rate, PurgeVial, wellplate, pump, mill)
                clear_well(rinse_vol, target_well, wellplate, pumping_rate, pump, PurgeVial, mill)
            
        
            ## Deposit DMF into well
            pipette(total_well_volume, Sol4, solution[i]['Target Well'], pumping_rate, PurgeVial, wellplate, pump, mill)        
            
            ## Echem CV - characterization
            echem.pstatcontrol.setfilename(target_well, 'CV')
            echem.exp.CV(echem.CVvi, echem.CVap1, echem.CVap2, echem.CVvf, echem.CVsr1, echem.CVsr2, echem.CVsr3, echem.CVsamplerate, echem.CVcycle)
            while active == True:
                client.PumpEvents(1)
                time.sleep(0.1)
            ## echem plot the data
            echem.pstatcontrol.plotdata(echem.CV)
            
            # Flushing procedure
            print('\nMoving to second flush with Sol3...')
            move_pipette_to_position(Sol1.coordinates['x'], Sol1.coordinates['y'], 0)
            move_pipette_to_position(Sol1.coordinates['x'], Sol1.coordinates['y'], Sol3.depth)
            print('Withdrawing Sol3...')
            withdraw(0.12,0.5,pump)
            move_pipette_to_position(Sol1.coordinates['x'], Sol1.coordinates['y'], 0)
            
            print('Moving to purge a second time...')
            move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
            move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
            print('Purging again...')
            purge(PurgeVial, 0.14)
            move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
            print('Solution run completed\n\n....................................................................\n')
        print('\n\n\t\t\tDEMO COMPLETED\n\n')
        
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print('Exception: ',e)
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)
      
    ## close out of serial connections
    mill.__exit__()    
    #serial.Serial("COM5", 19200).close()

if __name__ == '__main__':
    main()
else:
    pass
