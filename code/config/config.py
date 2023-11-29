"""The home of all project specific strings and values that are better to be set in one place than to be scattered around the code."""
from pathlib import Path

## Current working directory
PATH_TO_CODE = Path.cwd()

## Project files
MILL_CONFIG_FILE = PATH_TO_CODE / "code/config/mill_config.json"
WELLPLATE_CONFIG_FILE = PATH_TO_CODE / "code/config/wellplate_location.json"
PROJECT_LIST_FILE = PATH_TO_CODE / "code/system state/project_list.csv"
QUEUE_FILE = PATH_TO_CODE / "code/system state/queue.csv"
STOCK_STATUS_FILE = PATH_TO_CODE / "code/system state/stock_status.json"
WASTE_STATUS_FILE = PATH_TO_CODE / "code/system state/waste_status.json"
WELL_STATUS_FILE = PATH_TO_CODE / "code/system state/well_status.json"
WELL_TYPE_FILE = PATH_TO_CODE / "code/system state/well_type.csv"
PATH_TO_CONFIG = PATH_TO_CODE / "code/config/mill_config.json"
PATH_TO_LOCAL_WELL_HX = PATH_TO_CODE / "code/data/well_history.csv"

## Paths of project directories
PATH_TO_STATUS = PATH_TO_CODE / "code/system state/"
PATH_TO_COMPLETED_EXPERIMENTS = PATH_TO_CODE / "code/experiments_completed/"
PATH_TO_ERRORED_EXPERIMENTS = PATH_TO_CODE / "code/experiments_error/"
PATH_TO_DATA = PATH_TO_CODE / "data/"
PATH_TO_NETWORK_DATA = "p:/data/"
PATH_TO_NETWORK_WELL_HX = "p:/data/well_history.csv"
PATH_TO_LOGS = PATH_TO_CODE / "code/logs/"
PATH_TO_NETWORK_LOGS = "p:/logs/"
PATH_TO_EXPERIMENT_INBOX = PATH_TO_CODE / "code/experiments_inbox"
PATH_TO_EXPERIMENT_QUEUE = PATH_TO_CODE / "code/experiment_queue"

## Common values for the project
AIR_GAP = 40
DRIP_STOP = 5
PURGE_VOLUME = 20
