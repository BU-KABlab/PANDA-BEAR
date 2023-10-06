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
from typing import List, Dict, Tuple

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
PATH_TO_STATUS = "code/system state"
#PATH_TO_EXPERIMENT = "code/config/experiment.json"
MILL_CONNECTED = False
PSTAT_CONNECTED = False
PUMP_CONNECTED = False
SCALE_CONNECTED = False

def main():
    """Main function"""
    logger.info(printpanda())
    slack.send_slack_message('alert', 'ePANDA is starting up')

    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        ## Connect to equipment
        mill = Mill()
        MILL_CONNECTED = True
        mill.homing_sequence()
        echem.pstatconnect()
        PSTAT_CONNECTED = True
        # obs.OBS_controller()
        scale = Scale()
        SCALE_CONNECTED = True
        initial_weight = scale.value()
        logger.info("Connected to scale: %s", initial_weight)
        pump = Pump(mill=mill, scale=scale)
        PUMP_CONNECTED = True
        slack.send_slack_message('alert', 'ePANDA is connected to equipment')

        ## Initialize scheduler
        scheduler = Scheduler()

        ## Establish state of system
        stock_vials = vial_module.read_vials(Path.cwd() / PATH_TO_STATUS / "stock_status.json")
        waste_vials = vial_module.read_vials(Path.cwd() / PATH_TO_STATUS / "waste_status.json")
        wellplate = wellplate_module.Wells(a1_x=-218,a1_y= -74,orientation= 0,columns= "ABCDEFGH",rows= 13)

        logger.info("System state established")
        # read through the stock vials and log their name, contents, and volume
        for vial in stock_vials:
            logger.info("Stock vial %s contains %s with volume %d", vial.name, vial.contents, vial.volume)
        # read through the waste vials and log their name, contents, and volume
        for vial in waste_vials:
            logger.info("Waste vial %s contains %s with volume %d", vial.name, vial.contents, vial.volume)
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
                logger.info("No new experiments to run...waiting 1 minute for new experiments")
                time.sleep(60)
                ## Replace with slack alert and wait for response from user
                scheduler.check_inbox()

            # confirm that the new experiment is a valid experiment object
            if not isinstance(new_experiment, Experiment):
                logger.error("The experiment object is not valid")
                slack.send_slack_message('alert', 'An invalid experiment object was passed to the controller')
                break

            ## Initialize a results object
            experiment_results = ExperimentResult()
            ## Run experiments
            pre_experiment_status_msg = f"Running experiment {new_experiment.id}"
            logger.info(pre_experiment_status_msg)
            slack.send_slack_message('alert', pre_experiment_status_msg)

            updated_experiment, experiment_results = e_panda.run_experiment(
                instructions= new_experiment,
                results = experiment_results,
                mill= mill,
                pump= pump,
                scale = scale,
                stock_vials= stock_vials,
                waste_vials= waste_vials,
                wellplate= wellplate
                )

            post_experiment_status_msg = f"Experiment {updated_experiment.id} ended with status {updated_experiment.status}"
            logger.info(post_experiment_status_msg)
            slack.send_slack_message('alert', post_experiment_status_msg)

    except Exception as error:
        logger.error(error)
        slack.send_slack_message('alert', f"ePANDA encountered an error: {error}")
        raise error

    except KeyboardInterrupt as exc:
        logger.info("Keyboard interrupt detected")
        slack.send_slack_message('alert', 'ePANDA was interrupted by the user')
        raise KeyboardInterrupt from exc


    finally:
        ## close out of serial connections
        logger.info("Disconnecting from Mill, Pump, Pstat:")
        if SCALE_CONNECTED:
            scale.close()
            logger.info("Scale closed")
            SCALE_CONNECTED = False
        if PUMP_CONNECTED:
            #pump.close()
            logger.info("Pump closed")
            PUMP_CONNECTED = False
        if PSTAT_CONNECTED:
            echem.disconnectpstat()
            logger.info("Pstat closed")
            PSTAT_CONNECTED = False
        if MILL_CONNECTED:
            mill.home()
            mill.disconnect()
            logger.info("Mill closed")
            MILL_CONNECTED = False
        slack.send_slack_message('alert', 'ePANDA is shutting down...goodbye')

if __name__ == "__main__":
    main()
