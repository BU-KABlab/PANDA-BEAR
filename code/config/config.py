"""The home of all project specific strings and values that are better to be set in one place than to be scattered around the code."""
from pathlib import Path

## Current working directory
PATH_TO_CODE = Path.cwd() / "code"
NETWORK_DRIVE = Path("p:")
## Project File Names
MILL_CONFIG_FILE_NAME = "mill_config.json"
WELLPLATE_CONFIG_FILE_NAME = "wellplate_location.json"
PROJECT_LIST_FILE_NAME = "project_list.csv"
QUEUE_FILE_NAME = "queue.csv"
STOCK_STATUS_FILE_NAME = "stock_status.json"
WASTE_STATUS_FILE_NAME = "waste_status.json"
WELL_STATUS_FILE_NAME = "well_status.json"
WELL_TYPE_FILE_NAME = "well_type.csv"

## Paths of project directories
PATH_TO_STATUS = PATH_TO_CODE / "system state/"
PATH_TO_CONFIG = PATH_TO_CODE / "config/"
PATH_TO_COMPLETED_EXPERIMENTS = PATH_TO_CODE / "experiments_completed/"
PATH_TO_ERRORED_EXPERIMENTS = PATH_TO_CODE / "experiments_error/"
PATH_TO_DATA = PATH_TO_CODE / "data/"
PATH_TO_LOGS = PATH_TO_CODE / "logs/"
PATH_TO_EXPERIMENT_INBOX = PATH_TO_CODE / "experiments_inbox"
PATH_TO_EXPERIMENT_QUEUE = PATH_TO_CODE / "experiment_queue"
PATH_TO_NETWORK_DATA = NETWORK_DRIVE / "data/"
PATH_TO_NETWORK_LOGS = NETWORK_DRIVE / "logs/"
PATH_TO_NETWORK_STATUS = NETWORK_DRIVE / "system state/"

## Project files
MILL_CONFIG_FILE = PATH_TO_CONFIG / "mill_config.json"
WELLPLATE_CONFIG_FILE = PATH_TO_CONFIG / "wellplate_location.json"
PROJECT_LIST_FILE = PATH_TO_STATUS / "project_list.csv"
QUEUE_FILE = PATH_TO_STATUS / "queue.csv"
STOCK_STATUS_FILE = PATH_TO_STATUS / "stock_status.json"
WASTE_STATUS_FILE = PATH_TO_STATUS / "waste_status.json"
WELL_STATUS_FILE = PATH_TO_STATUS / "well_status.json"
PATH_TO_LOCAL_WELL_HX = PATH_TO_DATA / "well_history.csv"

PATH_TO_NETWORK_WELL_HX = PATH_TO_NETWORK_DATA / "well_history.csv"
PATH_TO_NETWORK_QUEUE = Path("p:") / "system state/queue.csv"

## Common values for the project
AIR_GAP = 40
DRIP_STOP = 5
PURGE_VOLUME = 20

## Validate that all paths exist
for path in [
    PATH_TO_STATUS,
    PATH_TO_CONFIG,
    PATH_TO_COMPLETED_EXPERIMENTS,
    PATH_TO_ERRORED_EXPERIMENTS,
    PATH_TO_DATA,
    PATH_TO_LOGS,
    PATH_TO_EXPERIMENT_INBOX,
    PATH_TO_EXPERIMENT_QUEUE,
]:
    if not path.exists():
        path.mkdir()

## Validate that all files exist
for file in [
    MILL_CONFIG_FILE,
    WELLPLATE_CONFIG_FILE,
    PROJECT_LIST_FILE,
    QUEUE_FILE,
    STOCK_STATUS_FILE,
    WASTE_STATUS_FILE,
    WELL_STATUS_FILE,
]:
    if not file.exists():
        file.touch()
