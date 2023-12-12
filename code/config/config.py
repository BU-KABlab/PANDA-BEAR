"""The home of all project specific strings and values that are 
better to be set in one place than to be scattered around the code."""
from pathlib import Path

## Project values
AIR_GAP = 40 #ul
DRIP_STOP = 5 #ul
PURGE_VOLUME = 20 #ul
RANDOM_FLAG = False # Set to True to randomize the order of the experiments

## Flag to use only local paths
USE_LOCAL_PATHS = False

## Define local repository path
LOCAL_REPO_PATH = Path.cwd().parent / "PANDA"

## Define network path
NETWORK_PATH = Path("//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/")

## Project File Names
__MILL_CONFIG_FILE_NAME = "mill_config.json"
__PROJECT_LIST_FILE_NAME = "project_list.csv"
__QUEUE_FILE_NAME = "queue.csv"
__SLACK_TICKETS_FILE_NAME = "slack_ticket_tracker.csv"
__STOCK_STATUS_FILE_NAME = "stock_status.json"
__WASTE_STATUS_FILE_NAME = "waste_status.json"
__WELL_STATUS_FILE_NAME = "well_status.json"
__WELL_TYPE_FILE_NAME = "well_type.csv"
__WELLPLATE_CONFIG_FILE_NAME = "wellplate_location.json"
__WELL_HISTORY = "well_history.csv"

## Project directory names
CODE = "code"
CONFIG = "config"
DATA = "data"
EXPERIMENT_INBOX = "experiments_inbox"
EXPERIMENT_QUEUE = "experiment_queue"
EXPERIMENTS_COMPLETED = "experiments_completed"
EXPERIMENTS_ERROR = "experiments_error"
LOGS = "logs"
SYS_STATE = "system state"

## Build complete paths for each project directory or file
if USE_LOCAL_PATHS:
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / CODE
    PATH_TO_SYSTEM_STATE = PATH_TO_CODE / SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / CONFIG
    PATH_TO_COMPLETED_EXPERIMENTS = PATH_TO_CODE / EXPERIMENTS_COMPLETED
    PATH_TO_ERRORED_EXPERIMENTS = PATH_TO_CODE / EXPERIMENTS_ERROR
    PATH_TO_DATA = LOCAL_REPO_PATH / DATA
    PATH_TO_LOGS = PATH_TO_CODE / LOGS
    PATH_TO_EXPERIMENT_INBOX = PATH_TO_CODE / EXPERIMENT_INBOX
    PATH_TO_EXPERIMENT_QUEUE = PATH_TO_CODE / EXPERIMENT_QUEUE
    PATH_TO_DATA = LOCAL_REPO_PATH / DATA
    PATH_TO_LOGS = PATH_TO_CODE / LOGS
    PATH_TO_STATUS = PATH_TO_CODE / SYS_STATE

    # Files
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    LOCAL_WELL_HX = PATH_TO_DATA / __WELL_HISTORY
    WELL_HX = PATH_TO_DATA / __WELL_HISTORY
    PROJECT_LIST = PATH_TO_STATUS / __PROJECT_LIST_FILE_NAME
    QUEUE = PATH_TO_STATUS / __QUEUE_FILE_NAME
    STOCK_STATUS = PATH_TO_SYSTEM_STATE / __STOCK_STATUS_FILE_NAME
    WASTE_STATUS = PATH_TO_SYSTEM_STATE / __WASTE_STATUS_FILE_NAME
    WELL_STATUS = PATH_TO_SYSTEM_STATE / __WELL_STATUS_FILE_NAME
    SLACK_TICKETS = PATH_TO_SYSTEM_STATE / __SLACK_TICKETS_FILE_NAME
    EPANDA_LOG = PATH_TO_LOGS / "ePANDA.log"

else: # Use network paths
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / CODE
    PATH_TO_SYSTEM_STATE = PATH_TO_CODE / SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / CONFIG
    PATH_TO_EXPERIMENT_INBOX = NETWORK_PATH / EXPERIMENT_INBOX
    PATH_TO_EXPERIMENT_QUEUE = NETWORK_PATH / EXPERIMENT_QUEUE
    PATH_TO_COMPLETED_EXPERIMENTS = NETWORK_PATH / EXPERIMENTS_COMPLETED
    PATH_TO_ERRORED_EXPERIMENTS = NETWORK_PATH / EXPERIMENTS_ERROR
    PATH_TO_DATA = NETWORK_PATH / DATA
    PATH_TO_LOGS = NETWORK_PATH / LOGS
    PATH_TO_NETWORK_DATA = NETWORK_PATH / DATA
    PATH_TO_NETWORK_LOGS = NETWORK_PATH / LOGS
    PATH_TO_NETWORK_STATUS = NETWORK_PATH / SYS_STATE

    #Files
    PROJECT_LIST = PATH_TO_SYSTEM_STATE / __PROJECT_LIST_FILE_NAME
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    WELL_HX = PATH_TO_NETWORK_DATA / __WELL_HISTORY
    QUEUE = PATH_TO_NETWORK_STATUS / __QUEUE_FILE_NAME
    STOCK_STATUS = PATH_TO_NETWORK_STATUS / __STOCK_STATUS_FILE_NAME
    WASTE_STATUS = PATH_TO_NETWORK_STATUS / __WASTE_STATUS_FILE_NAME
    WELL_STATUS = PATH_TO_NETWORK_STATUS / __WELL_STATUS_FILE_NAME
    SLACK_TICKETS = PATH_TO_NETWORK_LOGS / __SLACK_TICKETS_FILE_NAME
    EPANDA_LOG = PATH_TO_NETWORK_LOGS / "ePANDA.log"

## Validate that all paths exist and create them if they don't
for path in [
    PATH_TO_SYSTEM_STATE,
    PATH_TO_CONFIG,
    PATH_TO_COMPLETED_EXPERIMENTS,
    PATH_TO_ERRORED_EXPERIMENTS,
    PATH_TO_DATA,
    PATH_TO_LOGS,
    PATH_TO_EXPERIMENT_INBOX,
    PATH_TO_EXPERIMENT_QUEUE,
    PATH_TO_NETWORK_DATA,
    PATH_TO_NETWORK_LOGS,
    PATH_TO_NETWORK_STATUS,
]:
    path = Path(path)
    if not path.exists():
        print(f"Creating {path}")
        #path.mkdir()
        print(f"Created {path}")

## Validate that all files exist and create them if they don't
for file in [
    MILL_CONFIG,
    WELLPLATE_LOCATION,
    PROJECT_LIST,
    QUEUE,
    STOCK_STATUS,
    WASTE_STATUS,
    WELL_STATUS,
    WELL_HX,
    QUEUE,
    STOCK_STATUS,
    WASTE_STATUS,
    SLACK_TICKETS,
]:
    file_path = Path(PATH_TO_SYSTEM_STATE / file)
    if not file_path.exists():
        print(f"Creating {file_path}")
        #file_path.touch()
        print(f"Created {file_path}")
