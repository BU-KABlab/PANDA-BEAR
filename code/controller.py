"""
The controller is responsible for the following:
    - Running the scheduler and retriving the next experiment to run
    - checking the state of the system (vials, wells, etc.) 
    - Running the experiment (passing the experiment, system state, and instruments)
    - Recieve data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer

Additionally controller should be able to:
    - Reset the well statuses
    - Update the vial statuses
"""
# pylint: disable=line-too-long

# import standard libraries
import datetime
import json
import logging
from typing import Optional, Sequence, Union

# import third-party libraries
from pathlib import Path
from print_panda import printpanda
from mill_control import Mill
from mill_control import MockMill
from pump_control import Pump
from pump_control import MockPump

# import gamry_control_WIP as echem
# import gamry_control_WIP as echem
# import gamry_control_WIP_mock as echem_mock
from sartorius_local import Scale
from sartorius_local.mock import Scale as MockScale

# import obs_controls as obs
from slack_functions2 import SlackBot
from scheduler import Scheduler
import e_panda
from experiment_class import ExperimentResult, ExperimentBase, ExperimentStatus
from vials import StockVial, Vial2, WasteVial
import wellplate as wellplate_module

from config.config import (
    MILL_CONFIG_FILE,
    WELLPLATE_CONFIG_FILE,
    WELL_STATUS_FILE,
    PATH_TO_STATUS,
    PATH_TO_COMPLETED_EXPERIMENTS,
    PATH_TO_ERRORED_EXPERIMENTS,
    PATH_TO_NETWORK_DATA as PATH_TO_DATA,
    PATH_TO_NETWORK_LOGS as PATH_TO_LOGS,
    PATH_TO_NETWORK_WELL_HX as PATH_TO_WELL_HX,
    RANDOM_FLAG,
    STOCK_STATUS_FILE,
    WASTE_STATUS_FILE

)

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s")
system_handler = logging.FileHandler(PATH_TO_LOGS / "ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

# set up slack globally so that it can be used in the main function and others
slack = SlackBot()


def main(use_mock_instruments: bool = False, one_off: bool = False):
    """
    Main function

    Args:
    ----
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to False.
        one_off (bool, optional): Whether to run one experiment and then exit. Defaults to False.
    """
    print(printpanda())
    slack.test = use_mock_instruments
    slack.send_slack_message("alert", "ePANDA is starting up")
    toolkit = None
    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        ## Check for required files
        check_required_files()

        # Connect to equipment
        toolkit = connect_to_instruments(use_mock_instruments)
        logger.info("Connected to instruments")
        slack.send_slack_message("alert", "ePANDA has connected to equipment")

        ## Initialize scheduler
        scheduler = Scheduler()


        ## Establish state of system - we do this each time because each experiment changes the system state
        stock_vials, waste_vials, wellplate = establish_system_state()

        ## Flush the pipette tip with water before we start
        e_panda.flush_v2(stock_vials=stock_vials,
                            waste_vials=waste_vials,
                            flush_solution_name='water',
                            flush_volume=120,
                            pump=toolkit.pump,
                            mill=toolkit.mill,
                            )
        ## Update the system state with new vial and wellplate information
        update_vial_state_file(
            stock_vials, STOCK_STATUS_FILE
        )
        update_vial_state_file(
            waste_vials, WASTE_STATUS_FILE
        )

        ## Begin outer loop
        while True:
            ## Reset the logger to log to the ePANDA.log file and format
            experiment_formatter = logging.Formatter("%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s")
            system_handler.setFormatter(experiment_formatter)
            logger.addHandler(system_handler)

            ## Establish state of system - we do this each time because each experiment changes the system state
            stock_vials, waste_vials, wellplate = establish_system_state()

            ## Check the qeueue for any protocol type 2 experiments
            queue = scheduler.get_queue()
            # check if any of the experiments in the queue pandas dataframe are type 2
            protocol_type = 0
            for _, row in queue.iterrows():
                if row['protocol_type'] == 2:
                    protocol_type = 2
                    break

            if protocol_type in [0,1]:
                ## Ask the scheduler for the next experiment
                new_experiment, _ = scheduler.read_next_experiment_from_queue(random_pick=RANDOM_FLAG)
                # if new_experiment is None:
                #     slack.send_slack_message(
                #         "alert",
                #         "No new experiments to run...monitoring inbox for new experiments",
                #     )
                if new_experiment is None:
                    # e_panda.flush_pipette_tip(pump=toolkit.pump, 
                    #                           mill=toolkit.mill, 
                    #                           stock_vials=stock_vials, 
                    #                           waste_vials=waste_vials, 
                    #                           flush_solution_name='water',
                    #                           flush_volume=120,
                    #                           )
                    break # break out of the while True loop

                # while new_experiment is None:
                #     scheduler.check_inbox()
                #     new_experiment, _ = scheduler.read_next_experiment_from_queue()
                #     if new_experiment is not None:
                #         slack.send_slack_message(
                #             "alert", f"New experiment {new_experiment.id} found"
                #         )
                #         break # break out of the while new experiment is None loop
                #     logger.info(
                #         "No new experiments to run...waiting 5 minutes for new experiments"
                #     )
                #     time.sleep(600)
                #     # Replace with slack alert and wait for response from user

                ## confirm that the new experiment is a valid experiment object
                if not isinstance(new_experiment, ExperimentBase):
                    logger.error("The experiment object is not valid")
                    slack.send_slack_message(
                        "alert", "An invalid experiment object was passed to the controller"
                    )
                    break # break out of the while True loop

                ## Check that there is enough volume in the stock vials to run the experiment
                if not check_stock_vials(new_experiment, stock_vials):
                    error_message = f"Experiment {new_experiment.id} cannot be run because there is not enough volume in the stock vials"
                    slack.send_slack_message(
                        "alert",
                        error_message,
                    )
                    logger.error(error_message)
                    new_experiment.status = ExperimentStatus.ERROR
                    new_experiment.priority = 999
                    scheduler.update_experiment_status(new_experiment)
                    scheduler.update_experiment_queue_priority(
                        new_experiment.id, new_experiment.priority
                    )
                    break # break out of the while True loop

                ## Initialize a results object
                experiment_results = ExperimentResult(
                    id=new_experiment.id,
                    well_id=new_experiment.target_well,
                )
                # Announce the experiment
                pre_experiment_status_msg = f"Running experiment {new_experiment.id}"
                logger.info(pre_experiment_status_msg)
                slack.send_slack_message("alert", pre_experiment_status_msg)

                ## Update the experiment status to running
                new_experiment.status = ExperimentStatus.RUNNING
                new_experiment.status_date = datetime.datetime.now()
                scheduler.change_well_status_v2(wellplate.wells[new_experiment.target_well], new_experiment)

                ## Run the experiment
                e_panda.viscosity_experiments_protocol(
                    instructions=new_experiment,
                    results=experiment_results,
                    mill=toolkit.mill,
                    pump=toolkit.pump,
                    stock_vials=stock_vials,
                    waste_vials=waste_vials,
                    wellplate=wellplate,
                )

                ## Reset the logger to log to the ePANDA.log file and format
                system_handler.setFormatter(formatter)
                logger.addHandler(system_handler)

                ## Add the results to the experiment file
                new_experiment.results = experiment_results

                ## With returned experiment and results, update the experiment status and post the final status
                post_experiment_status_msg = f"Experiment {new_experiment.id} ended with status {new_experiment.status.value}"
                logger.info(post_experiment_status_msg)
                #slack.send_slack_message("alert", post_experiment_status_msg)

                ## Update the system state with new vial and wellplate information
                scheduler.change_well_status_v2(wellplate.wells[new_experiment.target_well], new_experiment)

                ## Update location of experiment instructions and save results
                scheduler.update_experiment_status(new_experiment)
                scheduler.update_experiment_location(new_experiment)
                scheduler.save_results(new_experiment, experiment_results)

                if one_off:
                    break # break out of the while True loop

            elif protocol_type == 2:
                ## Ask the scheduler for the list of type 2 protocols
                experiments_to_run = (
                    scheduler.generate_layered_protocol_experiment_list()
                )

                ## Check that there is enough volume in the stock vials to run the experiments
                for experiment in experiments_to_run:
                    if not check_stock_vials(experiment, stock_vials):
                        error_message = f"Experiment {experiment.id} cannot be run because there is not enough volume in the stock vials"
                        slack.send_slack_message(
                            "alert",
                            error_message,
                        )
                        logger.error(error_message)
                        input("Not enough volume in stock vials to run layered protocol. Press enter to continue or ctrl+c to exit")

                ## Initialize a results object
                for experiment in experiments_to_run:
                    experiment.results = ExperimentResult()

                e_panda.layered_solution_protocol(
                    instructions=experiments_to_run,
                    mill=toolkit.mill,
                    pump=toolkit.pump,
                    stock_vials=stock_vials,
                    waste_vials=waste_vials,
                    wellplate=wellplate,
                )

                ## Update location of experiment instructions and save results
                for experiment in experiments_to_run:
                    scheduler.update_experiment_status(experiment)
                    scheduler.update_experiment_location(experiment)
                    scheduler.save_results(experiment, experiment.results)

            ## Update the system state with new vial and wellplate information
            update_vial_state_file(
                stock_vials, Path.cwd() / PATH_TO_STATUS / "stock_status.json"
            )
            update_vial_state_file(
                waste_vials, Path.cwd() / PATH_TO_STATUS / "waste_status.json"
            )

    except Exception as error:
        logger.error(error)
        slack.send_slack_message("alert", f"ePANDA encountered an error: {error}")
        raise error

    except KeyboardInterrupt as exc:
        logger.info("Keyboard interrupt detected")
        slack.send_slack_message("alert", "ePANDA was interrupted by the user")
        raise KeyboardInterrupt from exc

    finally:
        # close out of serial connections
        if toolkit is not None:
            disconnect_from_instruments(toolkit)
        slack.send_slack_message("alert", "ePANDA is shutting down...goodbye")


class Toolkit:
    """A class to hold all of the instruments"""

    def __init__(self, mill: Union[Mill,MockMill], scale: Union[Scale, MockScale], pump: Union[Pump,MockPump], pstat = None):
        self.mill = mill
        self.scale = scale
        self.pump = pump
        self.pstat = pstat


def test_build_toolkit():
    """Test the building of the toolkit and checking that they are connected or not"""
    mill = Mill()
    scale = Scale()
    pump = Pump(mill=mill, scale=scale)
    instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
    return instruments


def check_required_files():
    """Confirm all required directories and files exist"""
    logger.info("Checking for required files and directories")
    required_files = [
        MILL_CONFIG_FILE,
        PATH_TO_STATUS,
        PATH_TO_COMPLETED_EXPERIMENTS,
        PATH_TO_ERRORED_EXPERIMENTS,
        PATH_TO_DATA,
        PATH_TO_LOGS,
    ]

    for file in required_files:
        if not Path(file).exists():
            logger.error("The %s is missing", file)
            slack.send_slack_message("alert", f"The {file} is missing")
            raise FileNotFoundError


def establish_system_state() -> (
    tuple[Sequence[StockVial], Sequence[WasteVial], wellplate_module.Wells2]
):
    """
    Establish state of system
    Returns:
        stock_vials (list[Vial]): list of stock vials
        waste_vials (list[Vial]): list of waste vials
        wellplate (wellplate_module.Wells): wellplate object
    """
    stock_vials = read_vials(PATH_TO_STATUS / "stock_status.json")
    waste_vials = read_vials(PATH_TO_STATUS / "waste_status.json")
    stock_vials_only = [vial for vial in stock_vials if isinstance(vial, StockVial)]
    waste_vials_only = [vial for vial in waste_vials if isinstance(vial, WasteVial)]
    wellplate = wellplate_module.Wells2(
        -230, -35, 0, columns="ABCDEFGH", rows=13, type_number=5
    )
    logger.info("System state established")

    ## read through the stock vials and log their name, contents, and volume
    for vial in stock_vials_only:
        logger.debug(
            "Stock vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any stock vials are empty, send a slack message prompting the user to refill them and confirm if program should continue
    empty_stock_vials = [vial for vial in stock_vials_only if vial.volume < 1000]
    if len(empty_stock_vials) > 0:
        slack.send_slack_message(
            "alert",
            "The following stock vials are low or empty: "
            + ", ".join([vial.name for vial in empty_stock_vials]),
        )
        slack.send_slack_message(
            "alert",
            "Please refill the stock vials and confirm in the terminal that the program should continue",
        )
        input(
            "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        )
        slack.send_slack_message("alert", "The program is continuing")

    ## read through the waste vials and log their name, contents, and volume
    for vial in waste_vials_only:
        logger.debug(
            "Waste vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any waste vials are full, send a slack message prompting the user to empty them and confirm if program should continue
    full_waste_vials = [vial for vial in waste_vials_only if vial.volume > 19000]
    if len(full_waste_vials) > 0:
        slack.send_slack_message(
            "alert",
            "The following waste vials are full: "
            + ", ".join([vial.name for vial in full_waste_vials]),
        )
        slack.send_slack_message(
            "alert",
            "Please empty the waste vials and confirm in the terminal that the program should continue",
        )
        input(
            "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        )
        slack.send_slack_message("alert", "The program is continuing")

    ## read the wellplate json and log the status of each well in a grid
    number_of_clear_wells = 0
    number_of_wells = 0
    with open(
        PATH_TO_STATUS / "well_status.json", "r", encoding="UTF-8"
    ) as file:
        wellplate_status = json.load(file)
    for well in wellplate_status["wells"]:
        number_of_wells += 1
        if well["status"] in ["clear", "new", "queued"]:
            number_of_clear_wells += 1
        # logger.debug(
        #     "Well %s has status %s", well["well_id"], well["status"]
        # )
    ## check that wellplate has the appropriate number of wells
    if number_of_wells != len(wellplate.wells):
        logger.error(
            "Wellplate status file does not have the correct number of wells. File may be corrupted"
        )
        raise ValueError
    logger.info("There are %d clear wells", number_of_clear_wells)
    if number_of_clear_wells == 0:
        # slack.send_slack_message("alert", "There are no clear wells on the wellplate")
        # slack.send_slack_message(
        #     "alert",
        #     "Please replace the wellplate and confirm in the terminal that the program should continue",
        # )
        # input(
        #     "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        # )
        # load_new_wellplate()
        # slack.send_slack_message("alert", "Wellplate has been reset. Continuing...")
        pass

    return stock_vials_only, waste_vials_only, wellplate


def check_stock_vials(experiment: ExperimentBase, stock_vials: Sequence[Vial2]) -> bool:
    """
    Check that there is enough volume in the stock vials to run the experiment

    Args:
        experiment (Experiment): The experiment to be run
        stock_vials (list[Vial]): The stock vials

    Returns:
        bool: True if there is enough volume in the stock vials to run the experiment
    """
    ## Check that the experiment has solutions and those soltuions are in the stock vials
    if len(experiment.solutions) == 0:
        logger.error("The experiment has no solutions")
        return False
    for solution in experiment.solutions:
        if str(solution).lower() not in [str(vial.name).lower() for vial in stock_vials]:
            logger.error(
                "The experiment requires solution %s but it is not in the stock vials",
                solution,
            )
            return False

    ## Check that there is enough volume in the stock vials to run the experiment
    ## Note there may be multiple of the same stock vial so we need to sum the volumes
    for solution in experiment.solutions:
        volume_required = experiment.solutions[solution]
        volume_available = sum(
            [vial.volume for vial in stock_vials if vial.name == solution]
        )
        if volume_available < volume_required:
            logger.error(
                "There is not enough volume of solution %s to run the experiment",
                solution,
            )
            return False
    return True


def connect_to_instruments(use_mock_instruments: bool = False):
    """Connect to the instruments"""
    if use_mock_instruments:
        logger.info("Using mock instruments")
        mill = MockMill()
        scale = MockScale()
        pump = MockPump(mill=mill, scale=scale)
        #pstat = echem_mock.GamryPotentiostat.connect()
        instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
        return instruments

    logger.info("Connecting to instruments:")
    mill = Mill()
    mill.homing_sequence()
    scale = Scale(address="COM6")
    pump = Pump(mill=mill, scale=scale)
    #pstat_connected = echem.pstatconnect()
    instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
    return instruments


def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    logger.info("Disconnecting from instruments:")
    instruments.mill.disconnect()
    # try:
    #     if echem.OPEN_CONNECTION:
    #         echem.pstatdisconnect()
    # except AttributeError:
    #     pass

    logger.info("Disconnected from instruments")


def read_vials(filename) -> Sequence[Union[StockVial, WasteVial]]:
    """
    Read in the virtual vials from the json file
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    list_of_solutions = []
    for items in vial_parameters:
        if items["name"] is not None:
            if items["category"] == 0:
                read_vial = StockVial(
                    name=str(items["name"]).lower(),
                    position=str(items["position"]).lower(),
                    volume=items["volume"],
                    capacity=items["capacity"],
                    density=items["density"],
                    coordinates={"x": items["x"], "y": items["y"]},
                    z_bottom=items["z_bottom"],
                    radius=items["radius"],
                    height=items["height"],
                    contamination=items["contamination"],
                    contents=items["contents"],
                    )
                list_of_solutions.append(read_vial)
            elif items["category"] == 1:
                read_vial = WasteVial(
                    name=str(items["name"]).lower(),
                    position=str(items["position"]).lower(),
                    volume=items["volume"],
                    capacity=items["capacity"],
                    density=items["density"],
                    coordinates={"x": items["x"], "y": items["y"]},
                    z_bottom=items["z_bottom"],
                    radius=items["radius"],
                    height=items["height"],
                    contamination=items["contamination"],
                    contents=items["contents"],
                    )
                list_of_solutions.append(read_vial)
    return list_of_solutions


def update_vial_state_file(vial_objects: Sequence[Vial2], filename):
    """
    Update the vials in the json file. This is used to update the volume and contamination of the vials
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    for vial in vial_objects:
        for vial_param in vial_parameters:
            if str(vial_param["position"]) == vial.position.lower():
                vial_param["volume"] = vial.volume
                vial_param["contamination"] = vial.contamination
                vial_param["contents"] = vial.contents
                break

    with open(filename_ob, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)

    return 0


def input_new_vial_values(vialgroup: str):
    """For user inputting the new vial values for the state file"""
    ## Fetch the current state file
    filename = ""
    if vialgroup == "stock":
        filename = Path.cwd() / PATH_TO_STATUS / "stock_status.json"
    elif vialgroup == "waste":
        filename = Path.cwd() / PATH_TO_STATUS / "waste_status.json"
    else:
        logger.error("Invalid vialgroup")
        raise ValueError

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Print the current vials and their values
    print("Current vials:")
    print(
        f"{'Position':<10} {'Name':<20} {'Contents':<20} {'Volume':<10} {'Capacity':<10} {'Contamination':<15}"
    )
    for vial in vial_parameters:
        print(
            f"{vial['position']:<10} {vial['name']:<20} {vial['contents']:<20} {vial['volume']:<10} {vial['capacity']:<10} {vial['contamination']:<15}"
        )

    ## Loop through each vial and ask for the new values except for position
    for vial in vial_parameters:
        print(f"\nVial {vial['position']}:")
        vial["name"] = input("Enter the name of the vial: ").lower()
        vial["contents"] = input("Enter the contents of the vial: ").lower()
        vial["volume"] = int(input("Enter the volume of the vial: "))
        vial["capacity"] = int(input("Enter the capacity of the vial: "))
        vial["contamination"] = input("Enter the contamination of the vial: ").lower()

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)


def reset_vials(vialgroup: str):
    """
    Resets the volume and contamination of the current vials to their capacity and 0 respectively

    Args:
        vialgroup (str): The group of vials to be reset. Either "stock" or "waste"
    """
    ## Fetch the current state file
    filename = ""
    if vialgroup == "stock":
        filename = Path.cwd() / PATH_TO_STATUS / "stock_status.json"
    elif vialgroup == "waste":
        filename = Path.cwd() / PATH_TO_STATUS / "waste_status.json"
    else:
        logger.error("Invalid vialgroup")
        raise ValueError

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Loop through each vial and set the volume and contamination
    for vial in vial_parameters:
        if vialgroup == "stock":
            vial["volume"] = vial["capacity"]
        elif vialgroup == "waste":
            vial["volume"] = 1000
            vial["contents"] = {}
        vial["contamination"] = 0

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)


def load_new_wellplate(ask: bool = False, new_plate_id: Optional[int] = None,new_wellplate_type_number: Optional[int] = None ) -> int:
    """
    Save the current wellplate, reset the well statuses to new.
    If no plate id or type number given assume same type number as the current wellplate and increment wellplate id by 1

    Args:
        new_plate_id (int, optional): The plate id being loaded. Defaults to None. If None, the plate id will be incremented by 1
        new_wellplate_type_number (int, optional): The type of wellplate. Defaults to None. If None, the type number will not be changed

    Returns:
        int
    """
    (
        current_wellplate_id,
        current_type_number,
        current_wellplate_is_new,
    ) = save_current_wellplate()

    if ask:
        new_plate_id = int(
            input("Enter the new wellplate id (Current id is {current_wellplate_id}): ")
        )
        new_wellplate_type_number = int(
            input(
                f"Enter the new wellplate type number (Current type is {current_type_number}): "
            )
        )
    else:
        if new_plate_id is None:
            new_plate_id = current_wellplate_id + 1
        if new_wellplate_type_number is None:
            new_wellplate_type_number = current_type_number

    well_status_file = WELL_STATUS_FILE
    if current_wellplate_is_new:
        return 0

    ## Go through a reset all fields and apply new plate id
    logger.debug("Resetting well statuses to new")
    new_wellplate = {
        "plate_id": new_plate_id,
        "type_number": new_wellplate_type_number,
        "wells": [
            {
                "well_id": chr(65 + (i // 12)) + str(i % 12 + 1),
                "status": "new",
                "status_date": "",
                "contents": {},
                "experiment_id": "",
                "project_id": "",
            }
            for i in range(96)
        ],
    }

    with open(well_status_file, "w", encoding="UTF-8") as file:
        json.dump(new_wellplate, file, indent=4)

    logger.debug("Well statuses reset to new")
    logger.info(
        "Wellplate %d saved and wellplate %d loaded",
        int(current_wellplate_id),
        int(new_plate_id),
    )
    return 0


def save_current_wellplate():
    """Save the current wellplate"""
    wellplate_is_new = True
    well_status_file = WELL_STATUS_FILE

    ## Go through a reset all fields and apply new plate id
    logger.debug("Saving wellplate")
    ## Open the current status file for the plate id , type number, and wells
    with open(well_status_file, "r", encoding="UTF-8") as file:
        current_wellplate = json.load(file)
    current_plate_id = current_wellplate["plate_id"]
    current_type_number = current_wellplate["type_number"]
    ## Check if the wellplate is new still or not
    for well in current_wellplate["wells"]:
        if well["status"] != "new":
            wellplate_is_new = False
            break

    ## Save each well to the well_history.csv file in the data folder even if it is empty
    ## plate id, type number, well id, experiment id, project id, status, status date, contents
    logger.debug("Saving well statuses to well_history.csv")

    # if the plate has been partially used before then there will be entries in the well_history.csv file
    # these entries will have the same plate id as the current wellplate
    # we want to write over these entries with the current well statuses

    # write back all lines that are not the same plate id as the current wellplate

    with open(PATH_TO_WELL_HX, "r", encoding="UTF-8") as input_file:
        with open(PATH_TO_DATA / "new_well_history.csv", "w", encoding="UTF-8") as output_file:
            for line in input_file:
                # Check if the line has the same plate ID as the current_plate_id
                if line.split(",")[0] == str(current_plate_id):
                    continue  # Skip this line
                # If the plate ID is different, write the line to the output file
                output_file.write(line)
    ## delete the old well_history.csv file
    Path(PATH_TO_WELL_HX).unlink()

    ## rename the new_well_history.csv file to well_history.csv
    Path(PATH_TO_DATA / "new_well_history.csv").rename(PATH_TO_WELL_HX)

    # write the current well statuses to the well_history.csv file
    with open(PATH_TO_WELL_HX, "a", encoding="UTF-8") as file:
        for well in current_wellplate["wells"]:
            # if the well is still queued then there is nothing in it and we can unallocated it
            if well["status"] == "queued":
                well["status"] = "new"
                well["experiment_id"] = ""
                well["project_id"] = ""

            file.write(
                f"{current_plate_id},{current_type_number},{well['well_id']},{well['experiment_id']},{well['project_id']},{well['status']},{well['status_date']},{well['contents']}"
            )
            file.write("\n")

    logger.debug("Wellplate saved")
    logger.info("Wellplate %d saved", int(current_plate_id))
    return int(current_plate_id), int(current_type_number), wellplate_is_new


def change_wellplate_location():
    """Change the location of the wellplate"""
    ## Load the working volume from mill_config.json
    with open(
        MILL_CONFIG_FILE, "r", encoding="UTF-8"
    ) as file:
        mill_config = json.load(file)
    working_volume = mill_config["working_volume"]

    ## Ask for the new location
    while True:
        new_location_x = float(input("Enter the new x location of the wellplate: "))

        if new_location_x > working_volume["x"] and new_location_x < 0:
            break

        print(
            f"Invalid input. Please enter a value between {working_volume['x']} and 0."
        )

    while True:
        new_location_y = float(input("Enter the new y location of the wellplate: "))

        if new_location_y > working_volume["y"] and new_location_y < 0:
            break

        print(
            f"Invalid input. Please enter a value between {working_volume['y']} and 0."
        )

    # Keep asking for input until the user enters a valid input
    while True:
        new_orientation = int(
            input(
                """
                Orientation of the wellplate:
                    0 - Vertical, wells become more negative from A1
                    1 - Vertical, wells become less negative from A1
                    2 - Horizontal, wells become more negative from A1
                    3 - Horizontal, wells become less negative from A1
                Enter the new orientation of the wellplate: 
                """
            )
        )
        if new_orientation in [0, 1, 2, 3]:
            break
        else:
            print("Invalid input. Please enter 0, 1, 2, or 3.")

    ## Get the current location config
    with open(
        WELLPLATE_CONFIG_FILE, "r", encoding="UTF-8"
    ) as file:
        current_location = json.load(file)

    new_location = {
        "x": new_location_x,
        "y": new_location_y,
        "orientation": new_orientation,
        "rows": current_location["rows"],
        "cols": current_location["cols"],
        "z-bottom": current_location["z-bottom"],
    }
    ## Write the new location to the wellplate_location.txt file
    with open(
        WELLPLATE_CONFIG_FILE, "w", encoding="UTF-8"
    ) as file:
        json.dump(new_location, file, indent=4)


if __name__ == "__main__":
    main(use_mock_instruments=False)
    # load_new_wellplate(new_plate_id=5)
