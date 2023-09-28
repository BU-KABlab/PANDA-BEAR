'''
The controller is responsible for the following:
    - Running the scheduler and retriving the next experiment to run
    - checking the state of the system (vials, wells, etc.) 
    - Running the experiment (passing the experiment, system state, and instruments)
    - Recieve data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer
'''
# pylint: disable=line-too-long

## import standard libraries
import logging
import time

## import third-party libraries
from pathlib import Path
from print_panda import printpanda
from mill_control import Mill
from pump_control import Pump
import gamry_control as echem
#import obs_controls as obs
import slack_functions as slack
from scheduler import Scheduler
import e_panda
from experiment_class import Experiment, ExperimentResult
import vials as vial_module
import wellplate as wellplate_module
from scale import Sartorius as Scale

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

PATH_TO_CONFIG = "code/config/mill_config.json"
PATH_TO_STATUS = "code/status"
PATH_TO_EXPERIMENT = "code/config/experiment.json"

def main():
    """Main function"""
    logger.info(printpanda())
    slack.send_slack_message('alert', 'ePANDA is starting up')

    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        ## Connect to equipment
        mill = Mill()
        pump = Pump()
        echem.pstatconnect()
        # obs.OBS_controller()
        scale = Scale()
        slack.send_slack_message('alert', 'ePANDA is connected to equipment')

        ## Initialize scheduler
        scheduler = Scheduler()

        ## Establish state of system
        stock_vials = vial_module.read_vials(Path.cwd() / PATH_TO_STATUS / "stock_status.json")
        waste_vials = vial_module.read_vials(Path.cwd() / PATH_TO_STATUS / "waste_status.json")
        wellplate = wellplate_module.Wells(-218, -74, 0, 0)

        logger.info("System state established")
        # read through the stock vials and log their name, contents, and volume
        for vial in stock_vials:
            logging.info("Stock vial %s contains %s with volume %d", vial.name, vial.contents, vial.volume)
        # read through the waste vials and log their name, contents, and volume
        for vial in waste_vials:
            logging.info("Waste vial %s contains %s with volume %d", vial.name, vial.contents, vial.volume)
        # read through the wellplate and log the status of each well


        ## On start up we want to run a baseline test
        # we are having the science team insert the control tests at the moment
        # uncomment the following lines to run the baseline test at startup
        # scheduler.insert_control_tests()
        # baseline = scheduler.read_next_experiment_from_queue()
        # baseline_results = ExperimentResult()
        # e_panda.run_experiment(baseline, baseline_results, mill, pump, stock_vials, waste_vials, wellplate)

        ## Begin outer loop
        while True:
            ## Ask the scheduler for the next experiment
            new_experiment, new_experiment_path = scheduler.read_next_experiment_from_queue()
            if new_experiment is None:
                logging.info("No new experiments to run...waiting 1 minute for new experiments")
                time.sleep(60)
                ## Replace with slack alert and wait for response from user
                scheduler.check_inbox()

            # confirm that the new experiment is a valid experiment object
            if not isinstance(new_experiment, Experiment):
                logging.error("The experiment object is not valid")
                slack.send_slack_message('alert', 'An invalid experiment object was passed to the controller')
                continue

            ## Initialize a results object
            experiment_results = ExperimentResult()
            ## Run experiments
            pre_experiment_status_msg = f"Running experiment {new_experiment} from {new_experiment_path}"
            logging.info(pre_experiment_status_msg)
            slack.send_slack_message('alert', pre_experiment_status_msg)

            experiment_results = e_panda.run_experiment(
                instructions= new_experiment,
                results = experiment_results,
                mill= mill,
                pump= pump,
                scale = scale,
                stock_vials= stock_vials,
                waste_vials= waste_vials,
                wellplate= wellplate
                )

            post_experiment_status_msg = f"Experiment {new_experiment.id} ended with status {new_experiment.status}"
            logging.info(post_experiment_status_msg)
            slack.send_slack_message('alert', post_experiment_status_msg)


    finally:
        ## Disconnect from equipment
        logging.info("Homing the mill...")
        mill.home()

        ## close out of serial connections
        logging.info("Disconnecting from Mill, Pump, Pstat:")
        mill.exit()
        logging.info("Mill closed")
        # pump.close()
        logging.info("Pump closed")
        echem.disconnectpstat()
        logging.info("Pstat closed")

        scale.close()
        logging.info("Scale closed")

        slack.send_slack_message('alert', 'ePANDA is shutting down...goodbye')
