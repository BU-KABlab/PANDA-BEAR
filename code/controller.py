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
from hmac import new
import json
import logging
import time

# import third-party libraries
from pathlib import Path
from wsgiref.validate import InputWrapper

from anyio import open_file
from print_panda import printpanda
from mill_control import MockMill as Mill
from pump_control import Pump
import gamry_control_WIP as echem

# import obs_controls as obs
import slack_functions as slack
from scheduler import Scheduler
import e_panda
from experiment_class import Experiment, ExperimentResult
from vials import Vial
import wellplate as wellplate_module
from scale import Sartorius as Scale

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

PATH_TO_CONFIG = "code/config/mill_config.json"
PATH_TO_STATUS = "code/system state"
PATH_TO_COMPLETED_EXPERIMENTS = "code/experiments_completed"
PATH_TO_ERRORED_EXPERIMENTS = "code/experiments_error"
PATH_TO_DATA = "data"
PATH_TO_LOGS = "code/logs"


def main():
    """Main function"""
    logger.info(printpanda())
    slack.send_slack_message("alert", "ePANDA is starting up")
    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        ## Check for required files
        check_required_files()

        # Connect to equipment
        # TODO clean this up and make it more robust
        toolkit = connect_to_instruments()
        mill = toolkit.mill
        scale = toolkit.scale
        pump = toolkit.pump
        logger.info("Connected to instruments")
        slack.send_slack_message("alert", "ePANDA has connected to equipment")

        ## Initialize scheduler
        scheduler = Scheduler()

        ## Begin outer loop
        while True:
            ## Establish state of system - we do this each time because each experiment changes the system state
            stock_vials, waste_vials, wellplate = establish_system_state()

            ## Ask the scheduler for the next experiment
            new_experiment, new_experiment_path = scheduler.read_next_experiment_from_queue()
            if new_experiment is None:
                logger.info(
                    "No new experiments to run...waiting 1 minute for new experiments"
                )
                time.sleep(60)
                # Replace with slack alert and wait for response from user
                scheduler.check_inbox()

            ## confirm that the new experiment is a valid experiment object
            if not isinstance(new_experiment, Experiment):
                logger.error("The experiment object is not valid")
                slack.send_slack_message(
                    "alert", "An invalid experiment object was passed to the controller"
                )
                break

            ## Initialize a results object
            experiment_results = ExperimentResult()
            # Announce the experiment
            pre_experiment_status_msg = f"Running experiment {new_experiment.id}"
            logger.info(pre_experiment_status_msg)
            slack.send_slack_message("alert", pre_experiment_status_msg)

            ## Update the experiment status to running
            new_experiment.status = "running"
            scheduler.change_well_status(new_experiment.target_well, "running")

            ## Run the experiment
            (
                updated_experiment,
                experiment_results,
                stock_vials,
                waste_vials,
                wellplate,
            ) = e_panda.run_experiment(
                instructions=new_experiment,
                results=experiment_results,
                mill=mill,
                pump=pump,
                stock_vials=stock_vials,
                waste_vials=waste_vials,
                wellplate=wellplate,
            )

            ## With returned experiment and results, update the experiment status and post the final status
            post_experiment_status_msg = f"Experiment {updated_experiment.id} ended with status {updated_experiment.status.value}"
            logger.info(post_experiment_status_msg)
            slack.send_slack_message("alert", post_experiment_status_msg)

            ## Update the system state with new vial and wellplate information
            scheduler.change_well_status(
                updated_experiment.target_well, updated_experiment.status, updated_experiment.status_date, updated_experiment.id
            )  # this function should probably be in the wellplate module
            update_vial_state_file(stock_vials, Path.cwd() / PATH_TO_STATUS / "stock_status.json")
            update_vial_state_file(waste_vials, Path.cwd() / PATH_TO_STATUS / "waste_status.json")

            ## Update location of experiment instructions and save results
            scheduler.update_experiment_status(updated_experiment)
            scheduler.update_experiment_location(updated_experiment)
            scheduler.save_results(updated_experiment, experiment_results)

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
        disconnect_from_instruments(toolkit)
        slack.send_slack_message("alert", "ePANDA is shutting down...goodbye")


class Toolkit:
    """A class to hold all of the instruments"""

    def __init__(self, mill: Mill, scale: Scale, pump: Pump, pstat):
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
        PATH_TO_CONFIG,
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


def establish_system_state() -> tuple[list[Vial], list[Vial], wellplate_module.Wells]:
    """
    Establish state of system
    Returns:
        stock_vials (list[Vial]): list of stock vials
        waste_vials (list[Vial]): list of waste vials
        wellplate (wellplate_module.Wells): wellplate object
    """
    stock_vials = read_vials(Path.cwd() / PATH_TO_STATUS / "stock_status.json")
    waste_vials = read_vials(Path.cwd() / PATH_TO_STATUS / "waste_status.json")
    wellplate = wellplate_module.Wells(
        a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13
    )
    logger.info("System state established")

    ## read through the stock vials and log their name, contents, and volume
    for vial in stock_vials:
        logger.debug(
            "Stock vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any stock vials are empty, send a slack message prompting the user to refill them and confirm if program should continue
    empty_stock_vials = [vial for vial in stock_vials if vial.volume < 1000]
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
    for vial in waste_vials:
        logger.debug(
            "Waste vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any waste vials are full, send a slack message prompting the user to empty them and confirm if program should continue
    full_waste_vials = [vial for vial in waste_vials if vial.volume > 19000]
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
    with open(Path.cwd() / PATH_TO_STATUS / "well_status.json", "r", encoding="UTF-8") as file:
        wellplate_status = json.load(file)
    for row in wellplate_status:
        for well in row:
            if well["status"] in ["clear", "new"]:
                number_of_clear_wells += 1
            logger.debug(
                "Well %s has status %s", well["name"], well["status"]
            )

    logger.info("There are %d clear wells", number_of_clear_wells)
    if number_of_clear_wells == 0:
        slack.send_slack_message("alert", "There are no clear wells on the wellplate")
        slack.send_slack_message(
            "alert",
            "Please replace the wellplate and confirm in the terminal that the program should continue",
        )
        input(
            "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        )
        load_new_wellplate()
        slack.send_slack_message("alert", "Wellplate has been reset. Continuing...")

    return stock_vials, waste_vials, wellplate


def connect_to_instruments():
    """Connect to the instruments"""
    mill = Mill()
    scale = Scale()
    pump = Pump(mill=mill, scale=scale)
    # pstat_connected = echem.pstatconnect()
    instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
    return instruments

def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    logger.info("Disconnecting from instruments:")
    instruments.mill.disconnect()
    instruments.scale.disconnect()
    instruments.pump.disconnect()
    if echem.OPEN_CONNECTION:
        echem.disconnectpstat()

    logger.info("Disconnected from instruments")

def read_vials(filename) -> list[Vial]:
    """
    Read in the virtual vials from the json file
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    list_of_solutions = []
    for items in vial_parameters:
        list_of_solutions.append(
            Vial(
                position=items["position"],
                x_coord=items["x"],
                y_coord=items["y"],
                volume=items["volume"],
                name=items["name"],
                contents=items["contents"],
                # capacity=items["capacity"],
                # bottom=items["bottom"],
                # height=items["height"],
                filepath=filename,
            )
        )
    return list_of_solutions

def update_vial_state_file(vial_objects: list[Vial], filename):
    """
    Update the vials in the json file
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    for vial in vial_objects:
        for items in vial_parameters:
            if items["name"] == vial.name:
                items["volume"] = vial.volume
                items["contamination"] = vial.contamination
                break

    with open(filename_ob, "w", encoding="ascii") as file:
        json.dump(vial_parameters, file, indent=4)

    return 0

def input_new_vial_values(vialgroup: str):
    """For user inputting the new vial values for the state file"""
    ## Fetch the current state file
    if vialgroup == "stock":
        filename = Path.cwd() / PATH_TO_STATUS / "stock_status.json"
    elif vialgroup == "waste":
        filename = Path.cwd() / PATH_TO_STATUS / "waste_status.json"

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Loop through each vial and ask for the new values except for position
    for vial in vial_parameters:
        print(f"Vial {vial['position']}")
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
    
    Valid vial groups are 'stock' and 'waste'
    """
    ## Fetch the current state file
    if vialgroup == "stock":
        filename = Path.cwd() / PATH_TO_STATUS / "stock_status.json"
    elif vialgroup == "waste":
        filename = Path.cwd() / PATH_TO_STATUS / "waste_status.json"

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Loop through each vial and ask for the new values except for position
    for vial in vial_parameters:
        vial["volume"] = vial["capacity"]
        vial["contamination"] = "0"

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)

def load_new_wellplate(override: bool = False, new_plate_id: int = None, new_wellplate_type_number: int = None) -> int:
    """
    Save the current wellplate, reset the well statuses to new. 
    If no plate id or type number given assume same type number and increment id by 1

    Args:
        override (bool, optional): Set to true to skip inputs. Defaults to False.
        new_plate_id (int, optional): The plate id being loaded. Defaults to None. If None, the plate id will be incremented by 1
        new_wellplate_type_number (int, optional): The type of wellplate. Defaults to None. If None, the type number will not be changed

    Returns:
        int
    """
    well_status_file = Path.cwd() / 'system state' / "well_status.json"
    # input("This will reset all well statuses to new. Press enter to continue.")

    # Confirm that the user wants this
    if override is False:
        choice = input(
            "This will reset all well statuses to new. Press enter to continue. Or enter 'n' to cancel: "
        )
        if choice == "n":
            return 0

    ## Open the current status file for the plate id , type number, and wells
    with open(well_status_file, "r", encoding="UTF-8") as file:
        current_wellplate = json.load(file)
    current_plate_id = current_wellplate["plate_id"]
    current_type_number = current_wellplate["type_number"]

    ## Save each well to the well_history.csv file in the data folder
    ## plate id, type number, well id, experiment id, project id, status, status date, contents
    logger.debug("Saving well statuses to well_history.csv")
    with open_file("data\\well_history.csv", "a", encoding="UTF-8") as file:
        for well in current_wellplate['wells']:
            file.write(f"{current_plate_id},{current_type_number},{well['well_id']},{well['experiment_id']},{well['project_id']},{well['status']},{well['status_date']},{well['contents']}\n")

    logger.debug("Well statuses saved to well_history.csv")

    ## If no plate id or type number given assume same type number and incremend id by 1
    if new_wellplate_type_number is None:
        new_wellplate_type_number = current_type_number

    if new_plate_id is None:
        new_plate_id = current_plate_id + 1

    ## Go through a reset all fields and apply new plate id
    logger.debug("Resetting well statuses to new")
    new_wellplate = current_wellplate
    new_wellplate["plate_id"] = new_plate_id
    new_wellplate["type_number"] = new_wellplate_type_number
    for well in new_wellplate['wells']:
        well["status"] = "new"
        well["status_date"] = ""
        well["experiment_id"] = ""
        well["project_id"] = ""

    with open(well_status_file, "w", encoding="UTF-8") as file:
        json.dump(new_wellplate, file, indent=4)

    logger.debug("Well statuses reset to new")
    logger.info("Wellplate %d saved and wellplate %d loaded", current_plate_id, new_plate_id)
    return 0


if __name__ == "__main__":
    main()
