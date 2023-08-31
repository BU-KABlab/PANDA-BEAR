'''
The controller is responsible for the following:
    - Running the scheduler and retriving the next experiment to run
    - checking the state of the system (vials, wells, etc.) 
    - Running the experiment (passing the experiment, system state, and instruments)
    - Recieve data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer
'''
import logging
import time


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
path_to_status = "code/config/status.json"
path_to_experiment = "code/config/experiment.json"
