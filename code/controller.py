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
import json
import logging
import time

# import third-party libraries
from pathlib import Path
from print_panda import printpanda
from mill_control import Mill
from mill_control import MockMill
from pump_control import Pump
from pump_control import MockPump

# import gamry_control_WIP as echem
import gamry_control_WIP_mock as echem
from sartorius import Scale
from sartorius.mock import Scale as MockScale

# import obs_controls as obs
import slack_functions as slack
from scheduler import Scheduler
import e_panda
from experiment_class import ExperimentResult, ExperimentBase, ExperimentStatus
from vials import StockVial, Vial, WasteVial
import wellplate as wellplate_module

from config.file_locations import (
    MILL_CONFIG_FILE,
    PATH_TO_STATUS,
    PATH_TO_COMPLETED_EXPERIMENTS,
    PATH_TO_ERRORED_EXPERIMENTS,
    PATH_TO_DATA,
    PATH_TO_LOGS,
)

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)


def main(use_mock_instruments: bool = False, workflow: int = 0):
    """
    Main function

    Args:
    ----
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to False.
        workflow (int, optional): The workflow to use. Defaults to 0
            0 - Standard workflow of running experiments one by one
            1 - Run a single experiment
            2 - Read all experiments in the queue, assign results to them, and then generate a list of solutions used.
                Pass this list of solutions to a protocol that expects the experiments to be given like this.
    """
    logger.info(printpanda())
    slack.send_slack_message("alert", "ePANDA is starting up")
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

        ## Begin outer loop
        while True:
            ## Ask the scheduler for the next experiment
            new_experiment, _ = scheduler.read_next_experiment_from_queue()
            if new_experiment is None:
                slack.send_slack_message(
                    "alert",
                    "No new experiments to run...monitoring inbox for new experiments",
                )
            while new_experiment is None:
                scheduler.check_inbox()
                new_experiment, _ = scheduler.read_next_experiment_from_queue()
                if new_experiment is not None:
                    slack.send_slack_message(
                        "alert", f"New experiment {new_experiment.id} found"
                    )
                    break
                logger.info(
                    "No new experiments to run...waiting 5 minutes for new experiments"
                )
                time.sleep(600)
                # Replace with slack alert and wait for response from user

            ## confirm that the new experiment is a valid experiment object
            if not isinstance(new_experiment, ExperimentBase):
                logger.error("The experiment object is not valid")
                slack.send_slack_message(
                    "alert", "An invalid experiment object was passed to the controller"
                )
                break

            ## Establish state of system - we do this each time because each experiment changes the system state
            stock_vials, waste_vials, wellplate = establish_system_state()

            ## Check that there is enough volume in the stock vials to run the experiment
            if not check_stock_vials(new_experiment, stock_vials):
                error_message = f"Experiment {new_experiment.id} cannot be run because there is not enough volume in the stock vials"
                slack.send_slack_message(
                    "alert",
                    error_message,
                )
                logger.error(error_message)
                new_experiment.status = "insufficient stock"
                new_experiment.priority = 999
                scheduler.update_experiment_status(new_experiment)
                scheduler.update_experiment_queue_priority(
                    new_experiment.id, new_experiment.priority
                )
                break

            ## Select appropriate workflow
            if workflow in [0, 1]:
                ## Initialize a results object
                experiment_results = ExperimentResult()
                # Announce the experiment
                pre_experiment_status_msg = f"Running experiment {new_experiment.id}"
                logger.info(pre_experiment_status_msg)
                slack.send_slack_message("alert", pre_experiment_status_msg)

                ## Update the experiment status to running
                new_experiment.status = ExperimentStatus.RUNNING
                scheduler.change_well_status(new_experiment.target_well, new_experiment)

                ## Run the experiment
                (
                    updated_experiment,
                    experiment_results,
                    stock_vials,
                    waste_vials,
                    wellplate,
                ) = e_panda.pipette_accurancy_protocol(
                    instructions=new_experiment,
                    results=experiment_results,
                    mill=toolkit.mill,
                    pump=toolkit.pump,
                    stock_vials=stock_vials,
                    waste_vials=waste_vials,
                    wellplate=wellplate,
                )

                ## Add the results to the experiment file
                updated_experiment.results = experiment_results

                ## With returned experiment and results, update the experiment status and post the final status
                post_experiment_status_msg = f"Experiment {updated_experiment.id} ended with status {updated_experiment.status.value}"
                logger.info(post_experiment_status_msg)
                slack.send_slack_message("alert", post_experiment_status_msg)

                ## Update the system state with new vial and wellplate information
                scheduler.change_well_status(
                    updated_experiment.target_well, updated_experiment
                )

                ## Update location of experiment instructions and save results
                scheduler.update_experiment_status(updated_experiment)
                scheduler.update_experiment_location(updated_experiment)
                scheduler.save_results(updated_experiment, experiment_results)

            if workflow == 1:
                break

            if workflow == 2:
                ## Initialize the list of experiments to be run (restricting to available wells)
                experiments_to_run = (
                    scheduler.generate_layered_protocol_experiment_list()
                )

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
    tuple[list[StockVial], list[WasteVial], wellplate_module.Wells]
):
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
        -230, -35, 0, columns="ABCDEFGH", rows=13, type_number=5
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
    number_of_wells = 0
    with open(
        Path.cwd() / PATH_TO_STATUS / "well_status.json", "r", encoding="UTF-8"
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


def check_stock_vials(experiment: ExperimentBase, stock_vials: list[Vial]) -> bool:
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
        if solution not in [vial.name for vial in stock_vials]:
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
        instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
        return instruments

    logger.info("Connecting to instruments:")
    mill = Mill()
    mill.homing_sequence()
    scale = Scale(address="COM6")
    pump = Pump(mill=mill, scale=scale)
    # pstat_connected = echem.pstatconnect()
    instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
    return instruments


def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    logger.info("Disconnecting from instruments:")
    instruments.mill.disconnect()
    # instruments.scale.close()
    try:
        if echem.OPEN_CONNECTION:
            echem.pstatdisconnect()
    except AttributeError:
        pass

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
        if items["name"] is not None:
            list_of_solutions.append(
                Vial(
                    position=items["position"],
                    x_coord=items["x"],
                    y_coord=items["y"],
                    volume=items["volume"],
                    name=items["name"],
                    contents=items["contents"],
                    capacity=items["capacity"],
                    contamination=items["contamination"],
                    filepath=filename,
                )
            )
    return list_of_solutions


def update_vial_state_file(vial_objects: list[Vial], filename):
    """
    Update the vials in the json file. This is used to update the volume and contamination of the vials
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    for vial in vial_objects:
        for vial_param in vial_parameters:
            if vial_param["position"] == vial.position:
                vial_param["volume"] = vial.volume
                vial_param["contamination"] = vial.contamination
                break

    with open(filename_ob, "w", encoding="UTF-8") as file:
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
    if vialgroup == "stock":
        filename = Path.cwd() / PATH_TO_STATUS / "stock_status.json"
    elif vialgroup == "waste":
        filename = Path.cwd() / PATH_TO_STATUS / "waste_status.json"

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Loop through each vial and set the volume and contamination
    for vial in vial_parameters:
        if vialgroup == "stock":
            vial["volume"] = vial["capacity"]
        elif vialgroup == "waste":
            vial["volume"] = 1000
        vial["contamination"] = "0"

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)


def load_new_wellplate(ask: bool = False) -> int:
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
        new_plate_id = current_wellplate_id + 1
        new_wellplate_type_number = current_type_number

    well_status_file = Path.cwd() / PATH_TO_STATUS / "well_status.json"
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
                "contents": [],
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
    well_status_file = Path.cwd() / PATH_TO_STATUS / "well_status.json"

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

    with open("data\\well_history.csv", "r", encoding="UTF-8") as input_file:
        with open("data\\new_well_history.csv", "w", encoding="UTF-8") as output_file:
            for line in input_file:
                # Check if the line has the same plate ID as the current_plate_id
                if line.split(",")[0] == str(current_plate_id):
                    continue  # Skip this line
                # If the plate ID is different, write the line to the output file
                output_file.write(line)
    ## delete the old well_history.csv file
    Path("data\\well_history.csv").unlink()

    ## rename the new_well_history.csv file to well_history.csv
    Path("data\\new_well_history.csv").rename("data\\well_history.csv")

    # write the current well statuses to the well_history.csv file
    with open("data\\well_history.csv", "a", encoding="UTF-8") as file:
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
        Path.cwd() / MILL_CONFIG_FILE / "mill_config.json", "r", encoding="UTF-8"
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
        Path.cwd() / MILL_CONFIG_FILE / "wellplate_location.json", "r", encoding="UTF-8"
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
        Path.cwd() / MILL_CONFIG_FILE / "wellplate_location.json", "w", encoding="UTF-8"
    ) as file:
        json.dump(new_location, file, indent=4)


if __name__ == "__main__":
    main(use_mock_instruments=False)
    # load_new_wellplate(new_plate_id=5)
