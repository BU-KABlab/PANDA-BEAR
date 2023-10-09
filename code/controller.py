"""
The controller is responsible for the following:
    - Running the scheduler and retriving the next experiment to run
    - checking the state of the system (vials, wells, etc.) 
    - Running the experiment (passing the experiment, system state, and instruments)
    - Recieve data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer
"""
# pylint: disable=line-too-long

# import standard libraries
import logging
import time

# import third-party libraries
from pathlib import Path
from print_panda import printpanda
from mill_control import Mill
from pump_control import Pump
import gamry_control as echem

# import obs_controls as obs
import slack_functions as slack
from scheduler import Scheduler
import e_panda
from experiment_class import Experiment, ExperimentResult
from vials import Vial, read_vials, update_vials
import wellplate as wellplate_module
from scale import Sartorius as Scale

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
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
    mill_connected = False
    pstat_connected = False
    pump_connected = False
    scale_connected = False
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
        mill_connected = True
        pstat_connected = True
        pump_connected = echem.pstatconnect()
        scale_connected = True
        logger.info("Connected to instruments")
        slack.send_slack_message("alert", "ePANDA has connected to equipment")

        ## Initialize scheduler
        scheduler = Scheduler()

        ## Establish state of system
        stock_vials, waste_vials, wellplate = establish_system_state()

        ## Begin outer loop
        while True:
            ## Ask the scheduler for the next experiment
            (
                new_experiment,
                new_experiment_path,
            ) = scheduler.read_next_experiment_from_queue()
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
                scale=scale,
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
                updated_experiment.target_well, updated_experiment.status
            )  # this function should probably be in the wellplate module
            update_vials(stock_vials, Path.cwd() / PATH_TO_STATUS / "stock_status.json")
            update_vials(waste_vials, Path.cwd() / PATH_TO_STATUS / "waste_status.json")

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
        logger.info("Disconnecting from instruments:")
        if scale_connected:
            scale.close()
            logger.info("Scale closed")
            scale_connected = False
        if pump_connected:
            # pump.close()
            logger.info("Pump closed")
            pump_connected = False
        if pstat_connected:
            echem.disconnectpstat()
            logger.info("Pstat closed")
            pstat_connected = False
        if mill_connected:
            mill.home()
            mill.disconnect()
            logger.info("Mill closed")
            mill_connected = False
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

    # read through the wellplate and log the status of each well in a grid
    number_of_clear_wells = 0
    for row in range(1, 13):
        for column in "ABCDEFGH":
            # logger.debug("Well %s%s is %s", column, row,
            #             wellplate.check_well_status(column+str(row)))
            if wellplate.check_well_status(column + str(row)) in ["clear", "new"]:
                number_of_clear_wells += 1
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
        slack.send_slack_message("alert", "The program is continuing")

    return stock_vials, waste_vials, wellplate


def connect_to_instruments():
    """Connect to the instruments"""
    mill = Mill()
    scale = Scale()
    pump = Pump(mill=mill, scale=scale)
    # pstat_connected = echem.pstatconnect()
    instruments = Toolkit(mill=mill, scale=scale, pump=pump, pstat=None)
    return instruments


if __name__ == "__main__":
    main()
