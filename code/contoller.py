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

import logging
import time
from print_panda import printpanda
from mill_control import Mill
from pump_control import Pump
import gamrycontrol as echem
import obs_controls as obs
import slack_functions as slack
from scheduler import Scheduler
import e_panda
from experiment_class import Experiment, ExperimentStatus, ExperimentResult
import vials as vial_module
from pathlib import Path
import wellplate as wellplate_module



## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("code/logs/controller.log")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)

path_to_config = "code/config/mill_config.json"
path_to_status = "code/status"
path_to_experiment = "code/config/experiment.json"

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

        ## Initialize scheduler
        scheduler = Scheduler()

        ## Establish state of system
        stock_vials = vial_module.read_vials(Path.cwd() / path_to_status / "stock_status.json")
        waste_vials = vial_module.read_vials(Path.cwd() / path_to_status / "waste_status.json")
        wellplate = wellplate_module.Wells(-218, -74, 0, 0)

        ## On start up we want to run a baseline test
        scheduler.insert_control_tests()
        baseline = scheduler.read_next_experiment_from_queue()
        baseline_results = ExperimentResult()
        e_panda.run_experiment(baseline, baseline_results, mill, pump, stock_vials, waste_vials, wellplate)

        ## Begin outer loop
        while True:
            ## Ask the scheduler for the next experiment
            new_experiment, new_experiment_path = scheduler.read_next_experiment_from_queue()
            if new_experiment is None:
                logging.info("No new experiments to run...waiting 1 minute for new experiments")
                time.sleep(60)
                ## Replace with slack alert and wait for response from user
                scheduler.check_inbox()

            ## Initialize a results object
            experiment_results = ExperimentResult()
            ## Run experiments
            logging.info("Running experiment %s", new_experiment)
            experiment_results = e_panda.run_experiment(new_experiment, experiment_results, mill, pump, stock_vials, waste_vials, wellplate)
            logging.info("Experiment %d ended with status %s", new_experiment.id, new_experiment.status)


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
        slack.send_slack_message('alert', 'ePANDA is shutting down')
