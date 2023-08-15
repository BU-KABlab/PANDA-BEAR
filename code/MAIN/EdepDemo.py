import time, nesp_lib, sys
from classes import Vial, MillControl, Wells
import gamrycontrol as echem
import comtypes.client as client
import print_panda
import json
import pathlib
import math

def main():
    ## Constants
    pumping_rate = 0.5
    RunTimes = {}
    char_sol_name = "Ferrocene"
    char_vol = 290
    flush_sol_name = "DMF"
    flush_vol = 120

    ## Common Variables
    month = time.strftime("%m")
    day = time.strftime("%d")
    year = time.strftime("%y")

    try:
        ## Program Set Up
        print_panda.printpanda()
        totalStartTime = int(time.time())

        print(f"Start Time: {totalStartTime}")
        print("Beginning protocol:\nConnecting to Mill, Pump, Pstat:")
        print("\tConnecting to Mill...")
        mill = MillControl()
        print("\tMill connected")  # Made an actual ccheck

        pump = set_up_pump()

        ## Initializing and connecting to pstat
        GamryCOM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
        pstat = client.CreateObject("GamryCOM.GamryPC6Pstat")
        devices = client.CreateObject("GamryCOM.GamryDeviceList")
        echem.pstat.Init(devices.EnumSections()[0])  # grab first pstat
        echem.pstat.Open()  # open connection to pstat
        print("\tPstat connected: ", devices.EnumSections()[0])

        # TODO Create proper exceptions for when things fail to connect,dont try and disconnect if they arent connected

        ## Set up wells
        wellplate = Wells(-218, -74, 0, 0)
        print("\tWells defined")

        ## Set up solutions
        waste_vials = read_vials("wasteParameters_08_07_23.json")
        stock_vials = read_vials("vialParameters_08_07_23.json")
        print("\tVials defined")

        ## Read instructions
        instruction_file = "campaign_3_23_08_07"
        instructions = read_instructions(instruction_file + ".json")

        print("\tExperiments defined")

        ## Run the experiments
        for i in range(len(instructions)):  # loop per well
            startTime = time.time()  # experiment start time
            well_run = instructions[i]["Target_Well"]
            wellStatus = instructions[i]["status"]
            RunTimes[well_run] = {}
            record_time_step(well_run, "Start", RunTimes)

            ## Deposit all experiment solutions into well
            experiment_solutions = ["Campaign3Mix"]
            for solution_name in experiment_solutions:
                print(
                    f"Pipetting {instructions[i][solution_name]} ul of {solution_name} into {well_run}..."
                )
                # soltuion_ml = float((instructions[i][solution_name])/1000000) #because the pump works in ml
                pipette(
                    volume=instructions[i][solution_name],  # volume in ul
                    solutions=stock_vials,
                    solution_name=solution_name,
                    target_well=well_run,
                    pumping_rate=pumping_rate,
                    waste_vials=waste_vials,
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                )
                if instructions[i][solution_name] > 0:
                    flush_pipette_tip(
                        pump,
                        waste_vials,
                        stock_vials,
                        flush_sol_name,
                        mill,
                        pumping_rate,
                        flush_vol,
                    )

            record_time_step(well_run, "Solutions", RunTimes)

            ## echem setup
            print("\n\nSetting up eChem experiments...")

            complete_file_name = echem.setfilename(well_run, "dep")

            ## echem CA - deposition
            print("\n\nBeginning eChem deposition of well: ", well_run)
            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                0,
            )  # move to safe height above target well
            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                wellplate.echem_height,
            )  # move to well depth
            echem.chrono(
                CAvi=echem.CAvi,
                CAti=echem.CAti,
                CAv1=instructions[i]["CAv1"],
                CAt1=echem.CAt1,
                CAv2=echem.CAv2,
                CAt2=echem.CAt2,
                CAsamplerate=echem.CAsamplerate,
            )  # CA
            while echem.active == True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            echem.plotdata("CA", complete_file_name)

            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                0,
            )  # move to safe height above target well

            record_time_step(well_run, "Deposition", RunTimes)

            ## Withdraw all well volume into waste
            clear_well(
                volume=wellplate.volume(well_run),
                target_well=well_run,
                wellplate=wellplate,
                pumping_rate=pumping_rate,
                pump=pump,
                waste_vials=waste_vials,
                mill=mill,
                solution_name="waste",
            )

            record_time_step(well_run, "Clear dep_sol", RunTimes)

            ## Rinse the well 3x
            rinse(
                wellplate, well_run, pumping_rate, pump, waste_vials, mill, stock_vials
            )

            record_time_step(well_run, "Rinse", RunTimes)

            print("\n\nBeginning eChem characterization of well: ", well_run)

            ## Deposit Ferrocene into well

            print(f"Infuse {char_sol_name} into well {well_run}...")
            pipette(
                volume=char_vol,
                solutions=stock_vials,
                solution_name=char_sol_name,
                target_well=well_run,
                pumping_rate=pumping_rate,
                waste_vials=waste_vials,
                waste_solution_name="waste",
                wellplate=wellplate,
                pump=pump,
                mill=mill,
            )

            record_time_step(well_run, "Deposit char_sol", RunTimes)

            ## Echem CV - characterization
            print(f"Characterizing well: {well_run}")
            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                0,
            )  # move to safe height above target well
            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                wellplate.echem_height,
            )
            complete_file_name = echem.setfilename(well_run, "CV")
            echem.cyclic(
                echem.CVvi,
                echem.CVap1,
                echem.CVap2,
                echem.CVvf,
                CVsr1=0.05,
                CVsr2=0.05,
                CVsr3=0.05,
                CVsamplerate=echem.CVsamplerate,
                CVcycle=echem.CVcycle,
            )
            while echem.active == True:
                client.PumpEvents(1)
                time.sleep(0.1)
            ## echem plot the data
            echem.plotdata("CV", complete_file_name)
            move_electrode_to_position(
                mill,
                wellplate.get_coordinates(well_run)["x"],
                wellplate.get_coordinates(well_run)["y"],
                0,
            )  # move to safe height above target well

            record_time_step(well_run, "Characterization", RunTimes)

            clear_well(
                char_vol,
                well_run,
                wellplate,
                pumping_rate,
                pump,
                waste_vials,
                mill,
                "waste",
            )

            record_time_step(well_run, "Clear Well", RunTimes)

            # Flushing procedure
            flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                flush_sol_name,
                mill,
                pumping_rate,
                flush_vol,
            )

            record_time_step(well_run, "Flush", RunTimes)

            ## Final rinse
            rinse(wellplate,
                  well_run,
                  pumping_rate,
                  pump,
                  waste_vials,
                  mill,
                  stock_vials
                  )
            record_time_step(well_run, 'Final Rinse', RunTimes)

            print(
                f"well {well_run} completed\n\n....................................................................\n"
            )
            wellStatus = "Completed"
            instructions[i]["status"] = wellStatus

            record_time_step(well_run, "End", RunTimes)

            wellTime = int(time.time())
            RunTimes[well_run]["Well Time"] = wellTime - startTime
            print(f'Well time: {RunTimes[well_run]["Well Time"]/60} minutes')

            save_runtime_data(
                RunTimes[well_run],
                f"{year}_{month}_{day}_{instruction_file}_Timestamps",
            )

            ## Print the current vial volumes in a table format
            print("\n\nCurrent Vial Volumes:")
            for vial in stock_vials:
                print(f"{vial.name}: {vial.volume} ml")
            print("\n\n")
            # TODO save the status of stock vials to a dataframe, saving the dataframe at the end of the campaign

        print("\n\nEXPERIMENTS COMPLETED\n\n")
        end_time = int(time.time())
        print(f"End Time: {end_time}")
        print(f"Total Time: {end_time - startTime}")
        print_runtime_data(RunTimes)

    except KeyboardInterrupt:
        print("Keyboard Interrupt")

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print("Exception: ", e)
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)
        instructions[i]["Status"] = "error"

    finally:
        ## Move electrode to frit bath
        print("Moving electrode to frit bath...")
        move_electrode_to_position(
            mill,
            wellplate.get_coordinates("H4")["x"],
            wellplate.get_coordinates("H4")["y"],
            0,
        )
        move_electrode_to_position(
            mill,
            wellplate.get_coordinates("H4")["x"],
            wellplate.get_coordinates("H4")["y"],
            wellplate.echem_height,
        )

        ## Save experiment instructions and status
        month = time.strftime("%m")
        day = time.strftime("%d")
        year = time.strftime("%y")
        filename = instruction_file
        cwd = pathlib.Path(__file__).parents[1]
        file_path = cwd / "instructions"
        file_folder = file_path / (year + "_" + month + "_" + day)
        pathlib.Path(file_folder).mkdir(parents=True, exist_ok=True)
        file_to_save = file_folder / filename
        with open(file_to_save, "w") as file:
            json.dump(instructions, file, indent=4)

        ## close out of serial connections
        print("Disconnecting from Mill, Pump, Pstat:")
        mill.__exit__()
        print("Mill closed")

        print("Pump closed")
        echem.disconnectpstat()
        print("Pstat closed")

        total_end_time = time.time()
        print(f"\n\nTotal Time: {total_end_time - totalStartTime}")
        print_runtime_data(RunTimes)

import logging


def read_json(filename: str):
    """
    Reads a JSON file and returns the data as a dictionary.
    :param filename: The name of the JSON file to read.
    :return: The data from the JSON file as a dictionary.
    """
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "instructions"
    file_to_open = file_path / filename
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file).dumps(data, indent=4)
    return data


def read_instructions(filename):
    instructions = []
    parameters = read_json(filename)
    for experiment in range(len(parameters["Experiments"])):
        instructions.append(parameters["Experiments"][experiment])
        instructions[experiment]["status"] = "qued"

    return instructions


def read_vials(filename):
    vial_parameters = read_json(filename)

    sol_objects = []
    for key, values in vial_parameters.items():
        for items in values:
            sol_objects.append(
                Vial(
                    x=items["x"],
                    y=items["y"],
                    volume=items["StartingVolume"],
                    name=items["name"],
                    contents=items["contents"],
                )
            )
    return sol_objects


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
    logging.info(f"\tPump found at address: {pump.address}")
    time.sleep(2)
    return pump


def withdraw(volume: float, rate: float, ser_pump: object):
    """
    Withdraw the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be withdrawn in milliliters but given as microliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to plunge from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    # Perform the withdrawl

    ## convert the volume argument from ul to ml
    volume = volume / 1000

    if (
        ser_pump.volume_withdrawn + volume > 0.2
    ):  # 0.2 is the maximum volume for the pipette tip
        raise Exception(
            f"The command to withdraw {volume} ml will overfill the 0.2 ml pipette with {ser_pump.volume_withdrawn} ml inside. Stopping run"
        )
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        ser_pump.pumping_volume = (
            volume  # Sets the pumping volume of the pump in units of milliliters.
        )
        ser_pump.pumping_rate = rate  # in units of milliliters per minute.
        ser_pump.run()
        logging.debug("\tWithdrawing...")
        time.sleep(0.5)
        while ser_pump.running:
            pass
        logging.debug("\tDone withdrawing")
        time.sleep(2)

        logging.debug(f"\tPump has withdrawn: {ser_pump.volume_withdrawn} ml")

    return 0


def infuse(volume: float, rate: float, ser_pump: object):
    """
    Infuse the given volume at the given rate and depth from the specified position.
    Args:
        volume (float): Volume to be infused in milliliters but given as microliters.
        position (dict): Dictionary containing x, y, and z coordinates of the position.
        depth (float): Depth to lower from the specified position in millimeters.
        rate (float): Pumping rate in milliliters per minute.
    """
    # then lower to the pipetting depth
    # move_pipette_to_position(position["x"], position["y"], depth)
    # Perform infusion

    ## convert the volume argument from ul to ml
    volume = volume / 1000

    if volume > 0.0:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
        ser_pump.pumping_volume = (
            volume  # Sets the pumping volume of the pump in units of milliliters.
        )
        ser_pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.run()
        logging.debug("\tInfusing...")
        time.sleep(0.5)
        while ser_pump.running:
            pass
        logging.debug("\tDone infusing")
        time.sleep(2)
        logging.debug(f"\tPump has infused: {ser_pump.volume_infused} ml")
    else:
        pass
    return 0


def move_center_to_position(mill: object, x, y, z):
    """
    Move the mill to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": 0, "y": 0, "z": 0}

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(command)
    return 0


## TODO Add a diagnoal move check to move pipette to position and move electrode to position functions


def move_pipette_to_position(
    mill: object,
    x,
    y,
    z=0.00,
):
    """
    Move the pipette to the specified coordinates.
    Args:
        x (float): X coordinate.
        y (float): Y coordinate.
        z (float): Z coordinate.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": -88, "y": 0, "z": 0}

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        x + offsets["x"], y + offsets["y"], z + offsets["z"]
    )  # x-coordinate has 84 mm offset for pipette location
    mill.execute_command(str(command))
    return 0


def move_electrode_to_position(mill: object, x, y, z):
    """
    Move the electrode to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": 36, "y": 30, "z": 0}
    # move to specified coordinates
    mill_move = "G0 X{} Y{} Z{}"
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(str(command))
    return 0


def purge(purge_vial: Vial, pump: object, purge_volume=20.00, pumping_rate=0.4):
    """
    Perform purging from the pipette.
    Args:
        volume (float): Volume to be purged in milliliters. Default is 0.02 ml.
        purge_vial_location (dict): Dictionary containing x, y, and z coordinates of the purge vial.
        purge_vial_depth (float): Depth to lower from the purge vial position in millimeters. Default is 0.00 mm.
    """
    infuse(purge_volume, pumping_rate, pump)
    purge_vial.update_volume(purge_volume)
    logging.debug(f"Purge vial new volume: {purge_vial.volume}")


def pipette(
    volume: float,  # volume in ul
    solutions: list,
    solution_name: str,
    target_well: str,
    pumping_rate: float,
    waste_vials: list,
    waste_solution_name: str,
    wellplate: Wells,
    pump: object,
    mill: object,
    purge_volume=20.00,
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
        repetitions = math.ceil(volume / 200)  # divide by pipette capacity (200 ul)
        repetition_vol = volume / repetitions
        for j in range(repetitions):
            logging.info(f"\n\nRepetition {j+1} of {repetitions}")
            solution = solution_selector(solutions, solution_name, repetition_vol)
            PurgeVial = waste_selector(waste_vials, waste_solution_name, repetition_vol)
            ## First half: pick up solution
            logging.info(f"Withdrawing {solution.name}...")
            move_pipette_to_position(
                mill, solution.coordinates["x"], solution.coordinates["y"], 0
            )  # start at safe height
            move_pipette_to_position(
                mill,
                solution.coordinates["x"],
                solution.coordinates["y"],
                solution.bottom,
            )  # go to solution depth (depth replaced with height)

            withdraw(repetition_vol + (2 * purge_volume), pumping_rate, pump)
            solution.update_volume(-(repetition_vol + 2 * purge_volume))
            logging.debug(f"{solution.name} new volume: {solution.volume}")
            move_pipette_to_position(
                mill, solution.coordinates["x"], solution.coordinates["y"], 0
            )  # return to safe height

            ## Intermediate: Purge
            logging.info("Purging...")
            move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )
            move_pipette_to_position(
                mill,
                PurgeVial.coordinates["x"],
                PurgeVial.coordinates["y"],
                PurgeVial.height,
            )  # PurgeVial.depth replaced with height
            purge(PurgeVial, pump, purge_volume)
            move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )

            ## Second Half: Deposit to well
            logging.info(f"Infusing {solution.name} into well {target_well}...")
            move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # start at safe height
            move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                wellplate.depth(target_well),
            )  # go to solution depth

            infuse(repetition_vol, pumping_rate, pump)
            wellplate.update_volume(target_well, repetition_vol)
            logging.info(f"Well {target_well} volume: {wellplate.volume(target_well)}")
            move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            ## Intermediate: Purge
            logging.info("Purging...")
            move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )
            move_pipette_to_position(
                mill,
                PurgeVial.coordinates["x"],
                PurgeVial.coordinates["y"],
                PurgeVial.height,
            )  # PurgeVial.depth replaced with height

            purge(PurgeVial, pump, purge_volume)
            move_pipette_to_position(
                mill, 
                PurgeVial.coordinates["x"], 
                PurgeVial.coordinates["y"], 0
            )

            logging.debug(
                f"Remaining volume in pipette: {pump.volume_withdrawn}"
            )  # should always be zero, pause if not
    else:
        pass


def clear_well(
    volume: float,
    target_well: str,
    wellplate: object,
    pumping_rate: float,
    pump: object,
    waste_vials: list,
    mill: object,
    solution_name="waste",
):
    """
    Clear the well of the specified volume with the specified solution

    Args:
        volume (float): Volume to be cleared in microliters
        target_well (str): The alphanumeric name of the well you would like to clear
        wellplate (Wells object): The wellplate object
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        mill (object): The mill object

    Returns:
        None
    """
    repititions = math.ceil(
        volume / 200
    )  # divide by 200 ul which is the pipette capacity to determin the number of repetitions
    repetition_vol = volume / repititions

    logging.info(
        f"\n\nClearing well {target_well} with {repititions}x repetitions of {repetition_vol} ..."
    )
    for j in range(repititions):
        PurgeVial = waste_selector(waste_vials, solution_name, repetition_vol)

        logging.info(f"Repitition {j+1} of {repititions}")
        move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # start at safe height
        # move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z']) # go to object top
        move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            wellplate.depth(target_well),
        )  # go to bottom of well
        withdraw(repetition_vol + 20, pumping_rate, pump)
        wellplate.update_volume(target_well, -repetition_vol)

        logging.debug(f"Well {target_well} volume: {wellplate.volume(target_well)}")
        move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # return to safe height

        logging.info("Moving to purge vial...")
        move_pipette_to_position(
            mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
        )
        # move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.coordinates['z'])
        move_pipette_to_position(
            mill,
            PurgeVial.coordinates["x"],
            PurgeVial.coordinates["y"],
            PurgeVial.height,
        )  # PurgeVial.depth replaced with height
        logging.info("Purging...")
        purge(PurgeVial, pump, repetition_vol + 20)  # repitition volume + 20 ul purge
        move_pipette_to_position(
            mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
        )
        # withdraw(20, pumping_rate, pump)
        # infuse(20, pumping_rate, pump)

        logging.info(f"Remaining volume in well: {wellplate.volume(target_well)}")


def print_runtime_data(runtime_data: dict):
    for well, data in runtime_data.items():
        logging.info(f"Well {well} Runtimes:")
        for section, runtime in data.items():
            minutes = runtime / 60
            logging.info(f"{section}: {minutes} seconds")


def rinse(
    wellplate: object,
    target_well: str,
    pumping_rate: float,
    pump: object,
    waste_vials: list,
    mill: object,
    solutions: list,
    rinse_repititions=3,
    rinse_vol=150,
):
    """
    Rinse the well with 150 ul of ACN
    """

    logging.info(f"Rinsing well {target_well} {rinse_repititions}x...")
    for r in range(rinse_repititions):  # 0, 1, 2...
        rinse_solution_name = "Rinse" + str(r)
        PurgeVial = waste_selector(waste_vials, rinse_solution_name, rinse_vol)
        # rinse_solution = solution_selector(solutions, rinse_solution_name, rinse_vol)
        logging.info(f"Rinse {r+1} of {rinse_repititions}")
        pipette(
            rinse_vol,
            solutions,
            rinse_solution_name,
            target_well,
            pumping_rate,
            waste_vials,
            rinse_solution_name,
            wellplate,
            pump,
            mill,
        )
        clear_well(
            rinse_vol,
            target_well,
            wellplate,
            pumping_rate,
            pump,
            waste_vials,
            mill,
            solution_name=rinse_solution_name,
        )


def flush_pipette_tip(
    pump: object,
    WasteVials: list,
    Solutions: list,
    flush_solution_name: str,
    mill: object,
    pumping_rate=0.4,
    flush_volume=120,
):
    """
    Flush the pipette tip with 120 ul of DMF
    """

    flush_solution = solution_selector(Solutions, flush_solution_name, flush_volume)
    PurgeVial = waste_selector(WasteVials, "waste", flush_volume)

    logging.info(f"\n\nFlushing with {flush_solution.name}...")
    move_pipette_to_position(
        mill, flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )
    withdraw(20, pumping_rate, pump)
    move_pipette_to_position(
        mill,
        flush_solution.coordinates["x"],
        flush_solution.coordinates["y"],
        flush_solution.bottom,
    )  # depth replaced with height
    logging.debug(f"\tWithdrawing {flush_solution.name}...")
    withdraw(flush_volume, pumping_rate, pump)
    move_pipette_to_position(
        mill, flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )

    logging.debug("\tMoving to purge...")
    move_pipette_to_position(
        mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
    )
    move_pipette_to_position(
        mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], PurgeVial.height
    )  # PurgeVial.depth replaced with height
    logging.debug("\tPurging...")
    purge(PurgeVial, pump, flush_volume + 20)
    move_pipette_to_position(
        mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
    )  # move back to safe height (top)


def solution_selector(solutions: list, solution_name: str, volume: float):
    """
    Select the solution from the list of solutions
    """
    for solution in solutions:
        if solution.name == solution_name and solution.volume > (volume + 1000):
            return solution
        else:
            pass
    raise Exception(f"{solution_name} not found in list of solutions")


def waste_selector(solutions: list, solution_name: str, volume: float):
    """
    Select the solution from the list of solutions
    """
    solution_found = False
    for solution in solutions:
        if (
            solution.name == solution_name
            and (solution.volume + volume) < solution.capacity
        ):
            solution_found = True
            return solution
        else:
            pass
    if solution_found == False:
        raise Exception(f"{solution_name} not found in list of solutions")


def record_time_step(well: str, step: str, run_times: dict):
    currentTime = int(time.time())
    sub_key = step + " Time"
    if well not in run_times:
        run_times[well] = {}
        run_times[well][sub_key] = currentTime
    else:
        run_times[well][sub_key] = currentTime
    # print(f'{step} time: {run_times[well][sub_key]}')


def record_stock_solution_hx(
    stock_sols: dict, waste_sol: dict, stock_solution_hx: dict
):
    pass


def save_runtime_data(run_times: dict, filename: str):
    """Save the run times to a json file in code/run_times"""
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "run_times"
    file_to_save = file_path / (filename + ".json")
    with open(file_to_save, "w") as f:
        json.dump(run_times, f)



if __name__ == "__main__":
    
    #logging.basicConfig(level=20)
    main()
else:
    pass
