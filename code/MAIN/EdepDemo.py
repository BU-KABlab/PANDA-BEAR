import time, nesp_lib, sys
from classes import Vial, MillControl, Wells
from generate_instructions import instruction_reader
import gamrycontrol as echem
import comtypes.client as client
import pathlib
import read_json as rj

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
        'x': -89,
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

def pipette(volume: float,
            solution: Vial,
            target_well: str,
            pumping_rate: float,
            PurgeVial: object,
            wellplate: Wells,
            pump: object,
            mill: object,
            purge_volume = 0.020
            ):
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
        print(f'Withdrawing {solution.name}...')
        move_pipette_to_position(mill, solution.coordinates['x'], solution.coordinates['y'], 0) # start at safe height
        move_pipette_to_position(mill, solution.coordinates['x'], solution.coordinates['y'], solution.depth) # go to soltuion depth
        
        if not solution.check_volume(-volume):
            print(f'Not enough {solution.name} to withdraw {volume} ml')
            raise Exception(f'Not enough {solution.name} to withdraw {volume} ml')
        withdraw(volume + 2 * purge_volume, pumping_rate, pump)
        solution.update_volume(-(volume + 2 * purge_volume))
        print(f'{solution.name} new volume: {solution.volume}')
        move_pipette_to_position(mill, solution.coordinates['x'],solution.coordinates['y'],0) # return to safe height
    
        ## Intermediate: Purge
        print('Purging...')
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
        if not PurgeVial.check_volume(+volume):
            print(f'{PurgeVial.name} is too full to add {volume} ml')
            raise Exception(f'{PurgeVial.name} is too full to add {volume} ml')
        purge(PurgeVial, pump, purge_volume)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        
        ## Second Half: Deposit to well
        print(f'Infusing {solution.name} into well {target_well}...')
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # start at safe height
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],wellplate.depth(target_well)) # go to solution depth
        if not wellplate.check_volume(well_id= target_well,added_volume=+volume):
            print(f'Well {target_well} is too full to add {volume} ml')
            raise Exception(f'Well {target_well} is too full to add {volume} ml')
        infuse(volume, pumping_rate, pump)
        wellplate.update_volume(target_well,volume)
        print(f'Well {target_well} volume: {wellplate.volume(target_well)}')
        move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'],wellplate.get_coordinates(target_well)['y'],0) # return to safe height
        
        ## Intermediate: Purge
        print('Purging...')
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], PurgeVial.depth)
        if not PurgeVial.check_volume(+volume):
            print(f'{PurgeVial.name} is too full to add {volume} ml')
            raise Exception(f'{PurgeVial.name} is too full to add {volume} ml')
        purge(PurgeVial, pump, purge_volume)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'], PurgeVial.coordinates['y'], 0)
        
        print(f"Remaining volume in pipette: {pump.volume_withdrawn}")
    else:
        pass

def clear_well(volume: float,
               target_well: str,
               wellplate: object,
               pumping_rate: float,
               pump: object,
               PurgeVial: Vial,
               mill: object):
    '''
    
    '''
    import math
    repititions = math.ceil(volume/0.200)
    repition_vol = volume/repititions
    
    print(f'\n\nClearing well {target_well} with {repititions}x repitions of {repition_vol} ...')
    for j in range(repititions):
        print(f'Repition {j+1} of {repititions}')
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
        if not PurgeVial.check_volume(+volume):
            print(f'{PurgeVial.name} is too full to add {volume} ml')
            raise Exception(f'{PurgeVial.name} is too full to add {volume} ml')
        purge(PurgeVial, pump, repition_vol + 0.02)
        move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
        
        print(f"Remaining volume in well: {wellplate.volume(target_well)}")

def print_runtime_data(runtime_data: dict):
    for well, data in runtime_data.items():
        print(f"Well {well} Runtimes:")
        for section, runtime in data.items():
            print(f"{section}: {runtime} seconds")
        print()

def rinse(wellplate : object,
          target_well: str,
          pumping_rate: float,
          pump: object,
          PurgeVial: Vial,
          mill: object,
          rinse_sol: Vial,
          rinse_repititions = 3,
          rinse_vol = 0.150):
    '''
    Rinse the well with 0.150 ml of ACN
    '''
    print(f'Rinsing well {target_well} 3x...')
    for i in range(rinse_repititions):
        print(f'Rinse {i+1} of {rinse_repititions}')
        pipette(rinse_vol, rinse_sol, target_well, pumping_rate, PurgeVial, wellplate, pump, mill)
        clear_well(rinse_vol, target_well, wellplate, pumping_rate, pump, PurgeVial, mill)

def flush_pipette_tip(pump: object,
                      PurgeVial: Vial,
                      flush_solution: Vial,
                      mill: object,
                      pumping_rate = 0.4,
                      flush_volume = 0.12
                      ):
    '''
    Flush the pipette tip with 0.12 ml of DMF
    '''
    print(f'\n\nFlushing with {flush_solution.name}...')
    move_pipette_to_position(mill,flush_solution.coordinates['x'], flush_solution.coordinates['y'], 0)
    move_pipette_to_position(mill,flush_solution.coordinates['x'], flush_solution.coordinates['y'], flush_solution.depth)
    print(f'\tWithdrawing {flush_solution.name}...')
    withdraw(flush_volume, pumping_rate, pump)
    move_pipette_to_position(mill, flush_solution.coordinates['x'], flush_solution.coordinates['y'], 0)
    
    print('\tMoving to purge...')
    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)
    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.depth)
    if not PurgeVial.check_volume(0.12):
                print(f'{PurgeVial.name} is too full to add {0.12} ml')
                raise Exception(f'{PurgeVial.name} is too full to add {0.12} ml')
    print('\tPurging...')
    purge(PurgeVial, pump, flush_volume + 0.02)
    move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],0)

def main():
    # Constants
    pumping_rate = 0.5
    Well_Rows = 'ABCDEFGH'
    Well_Columns = 13
    RunTimes = {}

    try:
        ## Program Set Up
        totalStartTime = time.time()

        print(f'Start Time: {totalStartTime}')
        print('Beginning protocol:\nConnecting to Mill, Pump, Pstat:')
        print('\tConnecting to Mill...')
        mill = MillControl()
        print('\tMill connected')
       
        pump = set_up_pump()
        
        ## Set up wells
        wellplate = Wells(-218, -74, 0, 0)
        print('\tWells defined')
        
        ## Define locations of vials and their contents
        solutions = rj.read_json('vialParameters_07_22_23.json')

        PurgeVial = Vial(-2,-50,'waste',1.00, name='Purge Vial')
        Sol1 = Vial( -2,  -80, "Acetonitrile", 20.0, name = 'ACN')
        Sol2 = Vial( -2, -110, "PEG", 20.0, name = 'PEG')
        Sol3 = Vial( -2, -140, "Acrylate", 20.0, name = 'Acrylate')
        Sol4 = Vial( -2, -170, "DMF", 20.0, name = 'DMF')
        solutions = [Sol1, Sol2, Sol3, Sol4]
        print('\tVials defined')
        
        ## Set up experiments
        
        color1 = instruction_reader('sol1.csv', Sol1, Well_Rows, Well_Columns)
        color2 = instruction_reader('sol2.csv', Sol2, Well_Rows, Well_Columns)
        dilution = instruction_reader('sol3.csv', Sol3, Well_Rows, Well_Columns)
        water_layer = instruction_reader('water.csv', Sol3, Well_Rows, Well_Columns)
        experiments = [color1, color2, dilution, water_layer]
        experiments = [color1]
        print('\tExperiments defined')
        ## Run the experiments
    
        #initializing and connecting to pstat
        GamryCOM = client.GetModule(['{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}', 1, 0])
        pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
        devices = client.CreateObject('GamryCOM.GamryDeviceList')
        echem.pstat.Init(devices.EnumSections()[0])  # grab first pstat
        echem.pstat.Open() #open connection to pstat
        print('\tPstat connected: ',devices.EnumSections()[0])
        
        for i in range(23): #loop per well
            
            startTime = time.time()
            wellRun = experiments[0][i]['Target Well']
            RunTimes[wellRun] = {}
            RunTimes[wellRun]['Start Time'] = startTime
            
            ## Deposit all experiment solutions into well
            for solution in experiments:
                print(f"\npipetting {solution[i]['Pipette Volume']} ul from {solution[i]['Solution'].name}: {solution[i]['Solution'].contents} into well {solution[i]['Target Well']}")
                solution_volume = float((solution[i]['Pipette Volume'])/1000) #because the pump works in ml
                current_well = solution[i]['Target Well']
                pipette(solution_volume, solution[i]['Solution'], current_well, pumping_rate, PurgeVial, wellplate, pump, mill)
                flush_pipette_tip(pump, PurgeVial, Sol3, mill)

            solutionsTime = time.time()
            RunTimes[wellRun]['Solutions Time'] = solutionsTime - startTime
            print(f'\nSolutions time: {RunTimes[wellRun]["Solutions Time"]}')

            print('\n\nSetting up eChem experiments...')
            ## echem setup
            target_well = solution[i]['Target Well']            
            complete_file_name = echem.setfilename(target_well, 'dep')
            print("\n\nBeginning eChem deposition of well: ",target_well)
            ## echem CA - deposition
            move_electrode_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z'])
            echem.chrono(echem.CAvi, echem.CAti, echem.CAv1, echem.CAt1, echem.CAv2, echem.CAt2, echem.CAsamplerate) #CA
            while echem.active == True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            echem.plotdata('CA', complete_file_name)
            
            
            depositionTime = time.time()
            RunTimes[wellRun]['Deposition Time'] = depositionTime - solutionsTime
            print(f'Deposition time: {RunTimes[wellRun]["Deposition Time"]}')

            ## Withdraw all well volume            
            clear_well(wellplate.volume(target_well), target_well, wellplate, pumping_rate, pump, PurgeVial, mill)        
    
            ## Rinse the well 3x
            rinse(wellplate, target_well, pumping_rate, pump, PurgeVial, mill, Sol1)

            rinseTime = time.time()
            RunTimes[wellRun]['Rinse Time'] = rinseTime - depositionTime
            print(f'\nRinse time: {RunTimes[wellRun]["Rinse Time"]}')

            print("\n\nBeginning eChem characterization of well: ",target_well)
            ## Deposit DMF into well
            
            print(f"Infuse {Sol4.name} into well {target_well}...")
            pipette(0.25, Sol4, solution[i]['Target Well'], pumping_rate, PurgeVial, wellplate, pump, mill)        
            
            ## Echem CV - characterization
            print(f'Characterizing well: {target_well}')
            move_electrode_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z'])
            complete_file_name = echem.setfilename(target_well, 'CV')
            echem.cyclic(echem.CVvi, echem.CVap1, echem.CVap2, echem.CVvf, echem.CVsr1, echem.CVsr2, echem.CVsr3, echem.CVsamplerate, echem.CVcycle)
            while echem.active == True:
                client.PumpEvents(1)
                time.sleep(0.1)
            ## echem plot the data
            echem.plotdata('CV', complete_file_name)
            
            characterizationTime = time.time()
            RunTimes[wellRun]['Characterization Time'] = characterizationTime - rinseTime
            print(f'\nCharacterization time: {RunTimes[wellRun]["Characterization Time"]}')

            clear_well(0.25, target_well, wellplate, pumping_rate, pump, PurgeVial, mill)

            clearTime = time.time()
            RunTimes[wellRun]['Clear Well Time'] = clearTime- characterizationTime
            print(f'\Time to Clear Well: {RunTimes[wellRun]["Clear Well Time"]}')

            # Flushing procedure
            flush_pipette_tip(pump, PurgeVial, Sol3, mill)
            
            flushTime = time.time()
            RunTimes[wellRun]['Flush Time'] = flushTime - characterizationTime
            print(f'\nFlush time: {RunTimes[wellRun]["Flush Time"]}')

            print(f'well {target_well} completed\n\n....................................................................\n')

            wellTime = time.time()
            RunTimes[wellRun]['Well Time'] = wellTime - startTime
            print(f'Well time: {RunTimes[wellRun]["Well Time"]/60} minutes')

            ## Table of all Vials and their volumes at this stage in the run
            print('\n\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            print('\n\nVial Volumes:') 
            print(f'{PurgeVial.name}: {PurgeVial.volume}')
            for solution in solutions:
                print(f'{solution.name}: {solution.volume}')
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')    
    	
        print('\n\nEXPERIMENTS COMPLETED\n\n')
        endTime = time.time()
        print(f'End Time: {endTime}')
        print(f'Total Time: {endTime - startTime}')

    except KeyboardInterrupt:
        print('Keyboard Interrupt')

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print('Exception: ', e)
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)

    finally:
        ## close out of serial connections
        print('Disconnecting from Mill, Pump, Pstat:')
        mill.__exit__()
        print('Mill closed')

        print('Pump closed')
        echem.disconnectpstat()
        print('Pstat closed')

        totalEndTime = time.time()
        print(f'\n\nTotal Time: {totalEndTime - totalStartTime}')
        print_runtime_data(RunTimes)
if __name__ == '__main__':
    main()
else:
    pass
