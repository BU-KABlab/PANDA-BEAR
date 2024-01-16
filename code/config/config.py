"""The home of all project specific strings and values that are 
better to be set in one place than to be scattered around the code."""
from pathlib import Path

## Project values
AIR_GAP = 40  # ul
DRIP_STOP = 5  # ul
PURGE_VOLUME = 20  # ul
RANDOM_FLAG = False  # Set to True to randomize the order of the experiments
TESTING = True  # Set to True to run in testing mode
## Flag to use only local paths
USE_LOCAL_PATHS = TESTING

## Define local repository path
LOCAL_REPO_PATH = Path(__file__).parents[2]

## Define network path
NETWORK_PATH = Path(
    "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/"
)

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
__CODE = "code"
__CONFIG = "config"
__DATA = "data"
__EXPERIMENT_INBOX = "experiments_inbox"
__EXPERIMENT_QUEUE = "experiments_queue"
__EXPERIMENTS_COMPLETED = "experiments_completed"
__EXPERIMENTS_ERROR = "experiments_error"
__LOGS = "logs"
__SYS_STATE = "system state"

## Build complete paths for each project directory or file
if USE_LOCAL_PATHS:
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / __CODE
    PATH_TO_SYSTEM_STATE = PATH_TO_CODE / __SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / __CONFIG
    PATH_TO_COMPLETED_EXPERIMENTS = PATH_TO_CODE / __EXPERIMENTS_COMPLETED
    PATH_TO_ERRORED_EXPERIMENTS = PATH_TO_CODE / __EXPERIMENTS_ERROR
    PATH_TO_DATA = LOCAL_REPO_PATH / __DATA
    PATH_TO_LOGS = PATH_TO_CODE / __LOGS
    PATH_TO_EXPERIMENT_INBOX = PATH_TO_CODE / __EXPERIMENT_INBOX
    PATH_TO_EXPERIMENT_QUEUE = PATH_TO_CODE / __EXPERIMENT_QUEUE
    PATH_TO_DATA = LOCAL_REPO_PATH / __DATA
    PATH_TO_LOGS = PATH_TO_CODE / __LOGS
    PATH_TO_STATUS = PATH_TO_CODE / __SYS_STATE

    # Files
    PROJECT_LIST = PATH_TO_STATUS / __PROJECT_LIST_FILE_NAME
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    WELL_HX = PATH_TO_DATA / __WELL_HISTORY
    QUEUE = PATH_TO_STATUS / __QUEUE_FILE_NAME
    STOCK_STATUS = PATH_TO_SYSTEM_STATE / __STOCK_STATUS_FILE_NAME
    WASTE_STATUS = PATH_TO_SYSTEM_STATE / __WASTE_STATUS_FILE_NAME
    WELL_STATUS = PATH_TO_SYSTEM_STATE / __WELL_STATUS_FILE_NAME
    WELL_TYPE = PATH_TO_CONFIG / __WELL_TYPE_FILE_NAME
    SLACK_TICKETS = PATH_TO_SYSTEM_STATE / __SLACK_TICKETS_FILE_NAME
    EPANDA_LOG = PATH_TO_LOGS / "ePANDA.log"

    ## Validate that all paths exist and create them if they don't
    for path in [
        PATH_TO_CODE,
        PATH_TO_SYSTEM_STATE,
        PATH_TO_CONFIG,
        PATH_TO_COMPLETED_EXPERIMENTS,
        PATH_TO_ERRORED_EXPERIMENTS,
        PATH_TO_DATA,
        PATH_TO_LOGS,
        PATH_TO_EXPERIMENT_INBOX,
        PATH_TO_EXPERIMENT_QUEUE,
        PATH_TO_DATA,
        PATH_TO_LOGS,
        PATH_TO_STATUS,
    ]:
        path = Path(path)
        if not path.exists():
            # print(f"Creating {path}")
            path.mkdir()
            print(f"Created {path}")

else:  # Use network paths
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / __CODE
    PATH_TO_SYSTEM_STATE = NETWORK_PATH / __SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / __CONFIG
    PATH_TO_EXPERIMENT_INBOX = NETWORK_PATH / __EXPERIMENT_INBOX
    PATH_TO_EXPERIMENT_QUEUE = NETWORK_PATH / __EXPERIMENT_QUEUE
    PATH_TO_COMPLETED_EXPERIMENTS = NETWORK_PATH / __EXPERIMENTS_COMPLETED
    PATH_TO_ERRORED_EXPERIMENTS = NETWORK_PATH / __EXPERIMENTS_ERROR
    PATH_TO_DATA = NETWORK_PATH / __DATA
    PATH_TO_LOGS = NETWORK_PATH / __LOGS
    PATH_TO_DATA = NETWORK_PATH / __DATA
    PATH_TO_LOGS = NETWORK_PATH / __LOGS
    PATH_TO_STATUS = NETWORK_PATH / __SYS_STATE

    # Files
    PROJECT_LIST = PATH_TO_SYSTEM_STATE / __PROJECT_LIST_FILE_NAME
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    WELL_HX = PATH_TO_DATA / __WELL_HISTORY
    QUEUE = PATH_TO_STATUS / __QUEUE_FILE_NAME
    STOCK_STATUS = PATH_TO_STATUS / __STOCK_STATUS_FILE_NAME
    WASTE_STATUS = PATH_TO_STATUS / __WASTE_STATUS_FILE_NAME
    WELL_STATUS = PATH_TO_STATUS / __WELL_STATUS_FILE_NAME
    WELL_TYPE = PATH_TO_CONFIG / __WELL_TYPE_FILE_NAME
    SLACK_TICKETS = PATH_TO_LOGS / __SLACK_TICKETS_FILE_NAME
    EPANDA_LOG = PATH_TO_LOGS / "ePANDA.log"

    ## Validate that all paths exist and create them if they don't
    for path in [
        PATH_TO_CODE,
        PATH_TO_SYSTEM_STATE,
        PATH_TO_CONFIG,
        PATH_TO_EXPERIMENT_INBOX,
        PATH_TO_EXPERIMENT_QUEUE,
        PATH_TO_COMPLETED_EXPERIMENTS,
        PATH_TO_ERRORED_EXPERIMENTS,
        PATH_TO_DATA,
        PATH_TO_LOGS,
        PATH_TO_DATA,
        PATH_TO_LOGS,
        PATH_TO_STATUS,
    ]:
        path = Path(path)
        if not path.exists():
            # print(f"Creating {path}")
            path.mkdir()
            print(f"Created {path}")

## Validate that all files exist and create them if they don't
for file in [
    PROJECT_LIST,
    MILL_CONFIG,
    WELLPLATE_LOCATION,
    WELL_HX,
    QUEUE,
    STOCK_STATUS,
    WASTE_STATUS,
    WELL_STATUS,
    WELL_TYPE,
    SLACK_TICKETS,
    EPANDA_LOG,
]:
    file_path = Path(PATH_TO_SYSTEM_STATE / file)
    if not file_path.exists():
        # print(f"Creating {file_path}")
        file_path.touch()
        print(f"Created {file_path}")
