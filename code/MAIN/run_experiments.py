import time, nesp_lib, sys
from classes import Vial, MillControl, Wells
import gamrycontrol as echem
import comtypes.client as client
import print_panda
import json
import pathlib
import math
import logging
import os
import datetime
import obsws_python as obs
import Analyzer as analyzer

def read_vials(filename):
    cwd = pathlib.Path(__file__).parents[0]
    filename = cwd / filename
    vial_parameters = json.load(open(filename))

    sol_objects = []
    for key, values in vial_parameters.items():
        for items in values:
            sol_objects.append(
                Vial(
                    x=items["x"],
                    y=items["y"],
                    volume=items["volume"],
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
    # mill.move_pipette_to_position(position["x"], position["y"], depth)
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
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # start at safe height
            mill.move_pipette_to_position(
                mill,
                solution.coordinates["x"],
                solution.coordinates["y"],
                solution.bottom,
            )  # go to solution depth (depth replaced with height)

            withdraw(repetition_vol + (2 * purge_volume), pumping_rate, pump)
            solution.update_volume(-(repetition_vol + 2 * purge_volume))
            logging.debug(f"{solution.name} new volume: {solution.volume}")
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # return to safe height

            ## Intermediate: Purge
            logging.info("Purging...")
            mill.move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                mill,
                PurgeVial.coordinates["x"],
                PurgeVial.coordinates["y"],
                PurgeVial.height,
            )  # PurgeVial.depth replaced with height
            purge(PurgeVial, pump, purge_volume)
            mill.move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )

            ## Second Half: Deposit to well
            logging.info(f"Infusing {solution.name} into well {target_well}...")
            mill.move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # start at safe height
            mill.move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                wellplate.depth(target_well),
            )  # go to solution depth

            infuse(repetition_vol, pumping_rate, pump)
            wellplate.update_volume(target_well, repetition_vol)
            logging.info(f"Well {target_well} volume: {wellplate.volume(target_well)}")
            mill.move_pipette_to_position(
                mill,
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            ## Intermediate: Purge
            logging.info("Purging...")
            mill.move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                mill,
                PurgeVial.coordinates["x"],
                PurgeVial.coordinates["y"],
                PurgeVial.height,
            )  # PurgeVial.depth replaced with height

            purge(PurgeVial, pump, purge_volume)
            mill.move_pipette_to_position(
                mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
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
        mill.move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # start at safe height
        # mill.move_pipette_to_position(mill, wellplate.get_coordinates(target_well)['x'], wellplate.get_coordinates(target_well)['y'], wellplate.get_coordinates(target_well)['z']) # go to object top
        mill.move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            wellplate.depth(target_well),
        )  # go to bottom of well
        withdraw(repetition_vol + 20, pumping_rate, pump)
        wellplate.update_volume(target_well, -repetition_vol)

        logging.debug(f"Well {target_well} volume: {wellplate.volume(target_well)}")
        mill.move_pipette_to_position(
            mill,
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # return to safe height

        logging.info("Moving to purge vial...")
        mill.move_pipette_to_position(
            mill, PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
        )
        # mill.move_pipette_to_position(mill, PurgeVial.coordinates['x'],PurgeVial.coordinates['y'],PurgeVial.coordinates['z'])
        mill.move_pipette_to_position(
            mill,
            PurgeVial.coordinates["x"],
            PurgeVial.coordinates["y"],
            PurgeVial.height,
        )  # PurgeVial.depth replaced with height
        logging.info("Purging...")
        purge(PurgeVial, pump, repetition_vol + 20)  # repitition volume + 20 ul purge
        mill.move_pipette_to_position(
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
    stock_vials: list,
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
        # rinse_solution = solution_selector(stock_vials, rinse_solution_name, rinse_vol)
        logging.info(f"Rinse {r+1} of {rinse_repititions}")
        pipette(
            rinse_vol,
            stock_vials,
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
    write_json(stock_vials, "vial_status.json")
    write_json(waste_vials, "waste_status.json")

def flush_pipette_tip(
    pump: object,
    waste_vials: list,
    stock_vials: list,
    flush_solution_name: str,
    mill: object,
    pumping_rate=0.4,
    flush_volume=120,
):
    """
    Flush the pipette tip with 120 ul of DMF
    """

    flush_solution = solution_selector(stock_vials, flush_solution_name, flush_volume)
    PurgeVial = waste_selector(waste_vials, "waste", flush_volume)

    logging.info(f"\n\nFlushing with {flush_solution.name}...")
    mill.move_pipette_to_position(
        flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )
    withdraw(20, pumping_rate, pump)
    mill.move_pipette_to_position(
        mill,
        flush_solution.coordinates["x"],
        flush_solution.coordinates["y"],
        flush_solution.bottom,
    )  # depth replaced with height
    logging.debug(f"\tWithdrawing {flush_solution.name}...")
    withdraw(flush_volume, pumping_rate, pump)
    mill.move_pipette_to_position(
        flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )

    logging.debug("\tMoving to purge...")
    mill.move_pipette_to_position(
        PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
    )
    mill.move_pipette_to_position(
        PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], PurgeVial.height
    )  # PurgeVial.depth replaced with height
    logging.debug("\tPurging...")
    purge(PurgeVial, pump, flush_volume + 20)
    mill.move_pipette_to_position(
        PurgeVial.coordinates["x"], PurgeVial.coordinates["y"], 0
    )  # move back to safe height (top)
    write_json(stock_vials, "vial_status.json")
    write_json(waste_vials, "waste_status.json")

# def solution_selector(solutions: list, solution_name: str, volume: float):
#     """
#     Select the solution from the list of solutions
#     """
#     for solution in solutions:
#         if solution.name == solution_name and solution.volume > (volume + 1000):
#             return solution
#         else:
#             pass
#     raise Exception(f"{solution_name} not found in list of solutions")

def solution_selector(solution_name: str, volume: float):
    '''Selects the appropriate vial from the list of solutions in vial_status.json for the given solution name and volume'''
    with open('vial_status.json', 'r') as f:
        vial_status = json.load(f)
    for solution in vial_status['solutions']:
        if solution['name'] == solution_name and solution['volume'] > (volume + 1000):
            return solution
        else:
            pass
    raise Exception(f"{solution_name} not found in list of solutions or not enough volume in vial(s)")

# def waste_selector(solutions: list, solution_name: str, volume: float):
#     """
#     Select the solution from the list of solutions
#     """
#     solution_found = False
#     for solution in solutions:
#         if (
#             solution.name == solution_name
#             and (solution.volume + volume) < solution.capacity
#         ):
#             solution_found = True
#             return solution
#         else:
#             pass
#     if solution_found == False:
#         raise Exception(f"{solution_name} not found in list of solutions")

def waste_selector(solution_name:str, volume):
    '''Selects the appropriate vial from the list of waste vials in waste_status.json for the given solution name and volume'''
    with open('waste_status.json', 'r') as f:
        waste_status = json.load(f)
    for solution in waste_status['waste']:
        if solution['name'] == solution_name and (solution['volume'] + volume) < solution['capacity']:
            return solution
        else:
            pass
    raise Exception(f"{solution_name} not found in list of waste vials or not capacity vials")

def record_time_step(step: str, run_times: dict):
    currentTime = int(time.time())
    sub_key = step + " Time"
    run_times[sub_key] = currentTime
    # print(f'{step} time: {run_times[well][sub_key]}')

def save_runtime_data(run_times: dict, filename: str):
    """Save the run times to a json file in code/run_times"""
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "run_times"
    file_to_save = file_path / (filename + ".json")
    with open(file_to_save, "w") as f:
        json.dump(run_times, f)

def connect_to_pstat():
    ## Initializing and connecting to pstat
    GamryCOM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
    pstat = client.CreateObject("GamryCOM.GamryPC6Pstat")
    devices = client.CreateObject("GamryCOM.GamryDeviceList")
    echem.pstat.Init(devices.EnumSections()[0])  # grab first pstat
    echem.pstat.Open()  # open connection to pstat
    logging.info("\tPstat connected: ", devices.EnumSections()[0])

def check_well_status(well: str):
    """
    Checks the status of a well in well_status.json.
    :param well: The well to check.
    :return: The status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data["Wells"]:
            if well["Target_Well"] == well:
                return well["status"]

def choose_alternative_well(well: str):
    """
    Chooses an alternative well if the target well is not available.
    :param well: The well to check.
    :return: The alternative well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data["Wells"]:
            if well["status"] == "new":
                return well["Target_Well"]
        return "none"

def change_well_status(well: str, status: str):
    """
    Changes the status of a well in well_status.json.
    :param well: The well to change.
    :param status: The new status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for wells in data["Wells"]:
            if wells["Target_Well"] == well:
                wells["status"] = status
                wells["status_date"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d_%H_%M_%S"
                )
                break
    with open(file_to_open, "w") as file:
        json.dump(data, file, indent=4)

def read_new_experiments(filename: str):
    """
    Reads a JSON file and returns the experiment instructions/recipie as a dictionary.
    :param filename: The name of the JSON file to read.
    :return: The instructions/recipie from the JSON file as a dictionary.
    """
    experiments_read = 0
    complete = True
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiments_inbox"
    file_to_open = file_path / filename
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for experiment in data["Experiments"]:
            existing_status = experiment["status"]
            if existing_status != "new":
                continue
            # Get the target well and create a filename
            desired_well = experiment["Target_Well"]

            # Check if the well is available
            if check_well_status(desired_well) != "new":
                # Find the next available well
                target_well = choose_alternative_well(desired_well)
                if target_well == "none":
                    print(
                        f"No wells available for experiment originally for well {desired_well}."
                    )
                    complete = False
                    continue
                else:
                    print(
                        f"Experiment originally for well {desired_well} is now for well {target_well}."
                    )
                    experiment["Target_Well"] = target_well
            else:
                target_well = desired_well

            filename = (
                f"{datetime.datetime.now().strftime('%Y-%m-%d_%H')}_{target_well}.json"
            )

            # add additional information to the experiment
            experiment["filename"] = filename
            experiment["deposition:"] = ""
            experiment["characterization"] = ""
            experiment["time_stamps"] = []
            experiment["OCP_file"] = ""
            experiment["OCP_pass"] = None
            experiment["deposition_data_file"] = ""
            experiment["deposition_plot_file"] = ""
            experiment["characterization_data_file"] = ""
            experiment["characterization_plot_file"] = ""

            # Save the experiment as a separate file in the experiment_que subfolder
            subfolder_path = cwd / "experiment_queue"
            subfolder_path.mkdir(parents=True, exist_ok=True)
            file_to_save = subfolder_path / filename
            with open(file_to_save, "w") as outfile:
                json.dump(experiment, outfile, indent=4)

            # Change the status of the well
            change_well_status(target_well, "queued")
            experiment["filename"] = filename
            experiment["status"] = "queued"
            experiment["status_date"] = datetime.datetime.now().strftime(
                "%Y-%m-%d_%H_%M_%S"
            )

            # Add the experiment to the list of experiments read
            experiments_read += 1

    # Save the updated file
    with open(file_to_open, "w") as file:
        json.dump(data, file, indent=4)

    return experiments_read, complete

def check_inbox():
    """
    Checks the experiments inbox folder for new experiments.
    :return: the filename(s) of new experiments.
    """
    
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiments_inbox"
    count = 0
    for file in file_path.iterdir():
        if file.is_file():
            [count, complete] = read_new_experiments(file.name)

            # Move to archive the file if it has been read
            if complete:
                archive_path = file_path / "archive"
                archive_path.mkdir(parents=True, exist_ok=True)
                file.replace(archive_path / file.name)
                print(f"File {file.name} moved to archive.")
            else:
                print(
                    f"File {file.name} not moved to archive. Not all experiments read."
                )

    return count

def read_next_experiment_from_queue():
    """
    Reads the next experiment from the queue.
    :return: The next experiment.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiment_queue"

    ## if folder is not empty pick the first file in the queue
    if os.listdir(file_path):
        file_to_open = file_path / os.listdir(file_path)[0]
        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
        return data, file_to_open
    else:
        return None, None

def save_completed_instructions(instructions: list, filename: str):
    """Save the experiment instructions to either the completed or failed instructions folder.
    Delete the experiment from the instructions queue"""
    filename = filename.name
    cwd = pathlib.Path(__file__).parents[0]
    queue_file_path = cwd / "experiment_queue"
    completed_file_path = cwd / "experiments_completed"
    failed_file_path = cwd / "experiments_error"

    if instructions["status"] == "completed":
        file_to_save = completed_file_path / (filename)
    elif instructions["status"] == "error":
        file_to_save = failed_file_path / (filename)
    else:
        return False

    with open(file_to_save, "w") as f:
        json.dump(instructions, f, indent=4)
        print(f"Experiment {filename} saved to {file_to_save}.")

    os.remove(queue_file_path / (filename))
    print(f"Experiment {filename} removed from queue.")

    os.remove(queue_file_path / (filename))
    print(f"Experiment {filename} removed from queue.")

def write_json(data: dict, filename: str):
    """
    Writes a dictionary to a JSON file.
    :param data: The data to write to the JSON file.
    :param filename: The name of the JSON file to write to.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_save = cwd / filename
    with open(file_to_save, "w") as file:
        json.dump(data, file, indent=4)

def update_experiment_recipt(experiment: dict, item_to_update:str, value, filename: str):
    """
    Updates the experiment receipt with the new value.
    :param experiment: The experiment receipt to update.
    :param item_to_update: The item to update.
    :param value: The new value.
    :return: The updated experiment receipt.
    """
    experiment[item_to_update] = value

    # Save the updated file 
    with open(filename, "w") as file:
        json.dump(experiment, file, indent=4)
        

    return experiment

def deposition(current_well, instructions, mill, pump, wellplate, echem, analyzer, deposition_potential, dep_duration, sample_period, experiment_id):
    ## echem setup
        logging.info("\n\nSetting up eChem experiments...")

        ## echem OCP
        logging.info("\n\nBeginning eChem OCP of well: ", current_well)
        instructions["status"] = "ocp"
        mill.move_electrode_to_position(
            wellplate.get_coordinates(current_well)["x"],
            wellplate.get_coordinates(current_well)["y"],
            0,
        )  # move to safe height above target well
        mill.move_electrode_to_position(
            wellplate.get_coordinates(current_well)["x"],
            wellplate.get_coordinates(current_well)["y"],
            wellplate.echem_height,
        )  # move to well depth
        complete_file_name = echem.setfilename(current_well, "OCP")
        echem.ocp(
            echem.OCPvi,
            echem.OCPti,
            echem.OCPrate,
        )  # OCP
        echem.activecheck()
        instructions["OCP_file"] = complete_file_name
        instructions["OCP_pass"] = echem.check_vsig_range(complete_file_name.with_suffix('.txt'))

        ## echem CA - deposition
        if instructions["OCP_pass"]:
            logging.info("\n\nBeginning eChem deposition of well: ", current_well)
            instructions["status"] = "deposition"
            complete_file_name = echem.setfilename(experiment_id, 'CA')
            #cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
            echem.chrono(
                echem.CAvi,
                echem.CAti,
                CAv1=deposition_potential,
                deposition_time=dep_duration,
                CAv2=echem.CAv2,
                CAt2=echem.CAt2,
                CAsamplerate=sample_period #TODO confirm
            )  # CA
            print("made it to try")
            echem.activecheck()
            ## echem plot the data
            analyzer.plotdata('CV', complete_file_name)
        else:
            raise Exception("OCP failed")

        mill.move_electrode_to_position(
            wellplate.get_coordinates(current_well)["x"],
            wellplate.get_coordinates(current_well)["y"],
            0,
        )  # move to safe height above target well
        return 0

def characterization(current_well, instructions, mill, pump, wellplate, echem, analyzer, pumping_rate, char_sol, char_vol, experiment_id):
    logging.info(f"Characterizing well: {current_well}")
    ## echem OCP
    logging.info("\n\nBeginning eChem OCP of well: ", current_well)
    instructions["status"] = "ocp-char"
    mill.move_electrode_to_position(
        wellplate.get_coordinates(current_well)["x"],
        wellplate.get_coordinates(current_well)["y"],
        0,
    )  # move to safe height above target well
    mill.move_electrode_to_position(
        wellplate.get_coordinates(current_well)["x"],
        wellplate.get_coordinates(current_well)["y"],
        wellplate.echem_height,
    )  # move to well depth
    complete_file_name = echem.setfilename(current_well, "OCP_char")
    echem.ocp(
        echem.OCPvi,
        echem.OCPti,
        echem.OCPrate,
    )  # OCP
    echem.activecheck()
    instructions["OCP_char_file"] = complete_file_name
    instructions["OCP_char_pass"] = echem.check_vsig_range(complete_file_name.with_suffix('.txt'))

    ## echem CV - characterization
    if instructions["OCP_char_pass"]:
        if instructions["baseline"] == 1:
            test_type = "CV_baseline"
        else:
            test_type = "CV"
        complete_file_name = echem.setfilename(current_well, test_type)
        echem.cyclic(
            echem.CVvi,
            echem.CVap1,
            echem.CVap2,
            echem.CVvf,
            CVsr1=instructions["scan-rate"],
            CVsr2=instructions["scan-rate"],
            CVsr3=instructions["scan-rate"],
            CVsamplerate=echem.CVstep / instructions["scan-rate"],
            CVcycle=echem.CVcycle,
        )
        echem.activecheck()
        ## echem plot the data
        echem.plotdata("CV", complete_file_name)
        mill.move_electrode_to_position(
            wellplate.get_coordinates(current_well)["x"],
            wellplate.get_coordinates(current_well)["y"],
            0,
        )  # move to safe height above target well

def run_experiment(instructions, instructions_filename,mill, pump, logging_level=logging.INFO):
    ## Common Variables
    month = time.strftime("%m")
    day = time.strftime("%d")
    year = time.strftime("%Y")
    osbclient = obs.ReqClient(host='localhost', port=4455, password='PandaBear!', timeout=3)
    label = osbclient.get_input_settings("text")
    label.input_settings["text"]="ePANDA"
    label.input_settings["font"]["size"]=60
    

    ## Logging
    log_file = f"{year}-{month}-{day}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ## Constants

    try:
        ## Program Set Up
        logging.info(print_panda.printpanda())
        logging.info("Beginning protocol:\nConnecting to Mill, Pump, Pstat:")
        logging.info("Connecting to Mill...")

        ## Set up wells
        wellplate = Wells(-218, -74, 0, 0)
        logging.info("Wells defined")

        ## Set up solutions
        waste_vials = read_vials("waste_status.json")
        stock_vials = read_vials("vial_status.json")
        logging.info("Vials defined")

        logging.info(
            f"""Experiment Outline:
                    Experiment ID: {instructions["id"]}
                    Replicates: {instructions["replicates"]}
                    Target Well: {instructions["target_well"]}
                    Acrylate: {instructions["acrylate"]}
                    PEG: {instructions["peg"]}   
                    DMF: {instructions["dmf"]}
                    Ferrocene: {instructions["ferrocene"]}
                    Custom: {instructions["custom"]}
                    Deposition Time: {instructions["dep-duration"]}
                    Deposition Voltage: {instructions["dep-pot"]}
                    OCP: {instructions["ocp"]}
                    CA: {instructions["ca"]}
                    CV: {instructions["cv"]}
                    Baseline: {instructions["baseline"]}
                General Parameters:
                    Pumping Rate: {instructions['pump_rate']}
                    Charaterization Sol: {instructions["char_sol"]}
                    Characterization Vol: {instructions["char_vol"]}
                    Flush Sol: {instructions["flush_sol"]}
                    Flush Vol: {instructions["flush_vol"]}
                     """
        )

        ## Run the experiment
        experiment_id = instructions["id"]
        current_well = instructions["target_well"]
        replicates = instructions["replicates"]
        wellStatus = instructions["status"]
        run_times = {}
        record_time_step("Start", run_times)

        ## Fetch parameters from isntructions
        pumping_rate = instructions["pump_rate"]
        char_sol = instructions["char_sol"]
        char_vol = instructions["char_vol"]
        flush_sol = instructions["flush_sol"]
        flush_vol = instructions["flush_vol"]
        dep_duration = instructions["dep-duration"]
        deposition_potential = instructions["dep-pot"]
        scan_rate = instructions["scan-rate"]
        sample_period = instructions["sample-period"]

        video_information = f'''
        Experiment Parameters:
            Experiment ID: {experiment_id}
            Well: {current_well}
            Replicates: {replicates}
            Pumping Rate: {pumping_rate}
            Charaterization Sol: {char_sol} Vol: {char_vol}
            Flush Sol: {flush_sol} Vol: {flush_vol}
            Deposition Voltage: {deposition_potential}
            OCP Compelte: No
            Deposition Complete: No
            Characterization Complete: No
        '''
        osbclient.set_input_settings(video_information,label.input_settings,True)
        osbclient.start_record()

        ## Deposit all experiment solutions into well
        experiment_solutions = ["acrylate", "peg", "dmf", "ferrocene", "custom"]

        for solution_name in experiment_solutions:

            if instructions[solution_name] > 0:  # if there is a solution to deposit
                logging.info(
                    f"Pipetting {instructions[solution_name]} ul of {solution_name} into {current_well}..."
                )
                # soltuion_ml = float((instructions[solution_name])/1000000) #because the pump works in ml
                pipette(
                    volume=instructions[solution_name],  # volume in ul
                    solutions=stock_vials,
                    solution_name=solution_name,
                    target_well=current_well,
                    pumping_rate=pumping_rate,
                    waste_vials=waste_vials,
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                )

                flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    flush_sol,
                    mill,
                    pumping_rate,
                    flush_vol,
                )

        record_time_step("Pipetted solutions", run_times)
        write_json(stock_vials, "vial_status.json")
        write_json(waste_vials, "waste_status.json")

        if instructions["CA"] == 1:
            deposition(current_well, instructions, mill, pump, wellplate, echem, analyzer, deposition_potential, dep_duration, sample_period, experiment_id)

            record_time_step("Deposition completed", run_times)
        
            instructions["deposition"] = "completed" # TODO turn into function to update instructions
            update_experiment_recipt(instructions,"deposition","completed",instructions_filename)

            ## Withdraw all well volume into waste
            clear_well(
                volume=wellplate.volume(current_well),
                target_well=current_well,
                wellplate=wellplate,
                pumping_rate=pumping_rate,
                pump=pump,
                waste_vials=waste_vials,
                mill=mill,
                solution_name="waste",
            )

            write_json(stock_vials, "vial_status.json")
            write_json(waste_vials, "waste_status.json")

            record_time_step("Cleared dep_sol", run_times)

            ## Rinse the well 3x
            rinse(wellplate, current_well, pumping_rate, pump, waste_vials, mill, stock_vials, rinse_repititions=instructions["rinse_count"], rinse_vol=instructions["rinse_vol"])

            record_time_step("Rinsed well", run_times)

            logging.info("\n\nBeginning eChem characterization of well: ", current_well)

            ## Deposit characterization solution into well

            logging.info(f"Infuse {char_sol} into well {current_well}...")
            pipette(
                volume=char_vol,
                solutions=stock_vials,
                solution_name=char_sol,
                target_well=current_well,
                pumping_rate=pumping_rate,
                waste_vials=waste_vials,
                waste_solution_name="waste",
                wellplate=wellplate,
                pump=pump,
                mill=mill,
            )

            record_time_step("Deposited char_sol", run_times)

            write_json(stock_vials, "vial_status.json")
            write_json(waste_vials, "waste_status.json")

        ## Echem CV - characterization
        if instructions["CV"] == 1:
            characterization(current_well, instructions, mill, pump, wellplate, echem, analyzer, scan_rate, experiment_id)
        
            record_time_step("Characterization complete", run_times)

            clear_well(
                char_vol,
                current_well,
                wellplate,
                pumping_rate,
                pump,
                waste_vials,
                mill,
                "waste",
            )

            write_json(stock_vials, "vial_status.json")
            write_json(waste_vials, "waste_status.json")

            record_time_step("Well cleared", run_times)

            # Flushing procedure
            flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                flush_sol,
                mill,
                pumping_rate,
                flush_vol,
            )

            record_time_step("Pipette Flushed", run_times)

            write_json(stock_vials, "vial_status.json")
            write_json(waste_vials, "waste_status.json")

        # Final rinse
        rinse(wellplate, current_well, pumping_rate, pump, waste_vials, mill, stock_vials, rinse_repititions=instructions["rinse_count"], rinse_vol=instructions["rinse_vol"])
        record_time_step("Final Rinse", run_times)

        write_json(stock_vials, "vial_status.json")
        write_json(waste_vials, "waste_status.json")

        instructions["status"] = "complete"

        record_time_step("End", run_times)

        instructions["time_stamps"] = run_times

        # save the updated instructions with run times, and data file names
        save_completed_instructions(instructions, instructions_filename)
        logging.info(f"Saved completed instructions for well {experiment_id}")

        logging.info(f"EXPERIMENT {experiment_id} COMPLETED\n\n")
        print_runtime_data(run_times)
    
    except KeyboardInterrupt:
        logging.warning("Keyboard Interrupt")
        instructions["Status"] = "error"
        save_completed_instructions(instructions, instructions_filename)
        logging.info(f"Saved completed instructions for well {experiment_id}")
        return 2
    
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logging.error("Exception: ", e)
        logging.error("Exception type: ", exception_type)
        logging.error("File name: ", filename)
        logging.error("Line number: ", line_number)
        instructions["Status"] = "error"
        return 1
    
    finally:
        instructions["status_date"] = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    return 0

def main():

    ## Check inbox
    logging.info("Checking inbox for new experiments...")
    new_experiments = check_inbox()
    logging.info(f"{new_experiments} new experiments found")

    ## Connect to equipment
    mill = MillControl()
    pump = set_up_pump()
    connect_to_pstat()

    ## Read instructions
    while True:
        instructions, instructions_filename = read_next_experiment_from_queue()
        if instructions is None:
            logging.info("No instructions in queue")
            break
        else:
            logging.info("Instructions read from queue")
            logging.info(instructions)
            status = run_experiment(
                instructions, instructions_filename, logging_level=logging.DEBUG
                )
            logging.info("Experiment completed with code ", status)
            if status == 0:
                pass
            elif status == 1:
                logging.error("Experiment failed")
            elif status == 2:
                logging.warning("Experiment stopped by user")
                break
            else:
                pass

    ## Disconnect from equipment
    mill.home()

    ## close out of serial connections
    logging.info("Disconnecting from Mill, Pump, Pstat:")
    mill.__exit__()
    logging.info("Mill closed")

    logging.info("Pump closed")
    echem.disconnectpstat()
    logging.info("Pstat closed")

if __name__ == "__main__":
    # logging.basicConfig(level=20)
    main()
