"""The home of all project specific strings and values that are 
better to be set in one place than to be scattered around the code."""
from pathlib import Path

def get_repo_path():
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent
    return repo_path

def read_testing_config():
    """Reads the testing configuration file."""
    repo_path = get_repo_path()
    config_path = repo_path / "config" / "testing.txt"
    with open(config_path, "r", encoding="utf-8") as f:
        return f.read().strip() == "True"

def write_testing_config(value: bool):
    """Writes the testing configuration file."""
    repo_path = get_repo_path()
    config_path = repo_path / "config" / "testing.txt"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(str(value))## Project values

AIR_GAP = float(40.0)  # ul
DRIP_STOP = float(5.0)  # ul
PURGE_VOLUME = float(20)  # ul
RANDOM_FLAG = False  # Set to True to randomize the order of the experiments
DEFAULT_PUMPING_RATE = float(0.3)  # ul/s
## Testing flag
# testing.txt is the only place to change the mode besides from the main menue
# This should no be put into a db since depending on its setting a different db is used.
# TODO: instead of seperate dbs what about seperate schemas?
# TODO this is more of an environment variable file than config file, look into python-dotenv
## Flag to use only local paths
USE_LOCAL_PATHS = read_testing_config()

## Define local repository path
LOCAL_REPO_PATH = Path(__file__).parents[2]

## Define network path
NETWORK_PATH = Path(
    "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/"
)

## Project File Names
__MILL_CONFIG_FILE_NAME = "mill_config.json"
__WELLPLATE_CONFIG_FILE_NAME = "wellplate_location.json"

## Project directory names
__CODE = "epanda_lib"
__CONFIG = "config"
__DATA = "data"
__LOGS = "logs"
__SYS_STATE = "system state"

## FLIR Camera related - must be python 3.6
PYTHON_360_PATH = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")
CAMERA_SCRIPT_PATH = Path(LOCAL_REPO_PATH/__CODE/"camera.py")

## Build complete paths for each project directory or file
if USE_LOCAL_PATHS:
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / __CODE
    PATH_TO_SYSTEM_STATE = PATH_TO_CODE / __SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / __CONFIG
    PATH_TO_DATA = LOCAL_REPO_PATH / __DATA
    PATH_TO_LOGS = PATH_TO_CODE / __LOGS
    PATH_TO_DATA = LOCAL_REPO_PATH / __DATA
    PATH_TO_LOGS = LOCAL_REPO_PATH / __LOGS
    PATH_TO_STATUS = PATH_TO_CODE / __SYS_STATE

    # Files
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    EPANDA_LOG = PATH_TO_LOGS / "ePANDA.log"

    # DB
    SQL_DB_PATH = LOCAL_REPO_PATH /"epanda_test.db"

    ## Validate that all paths exist and create them if they don't
    for path in [
        PATH_TO_CODE,
        PATH_TO_SYSTEM_STATE,
        PATH_TO_CONFIG,
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

else:  # Use network paths
    # Directories
    PATH_TO_CODE = LOCAL_REPO_PATH / __CODE
    PATH_TO_SYSTEM_STATE = NETWORK_PATH / __SYS_STATE
    PATH_TO_CONFIG = PATH_TO_CODE / __CONFIG
    PATH_TO_DATA = NETWORK_PATH / __DATA
    PATH_TO_LOGS = NETWORK_PATH / __LOGS
    PATH_TO_DATA = NETWORK_PATH / __DATA
    PATH_TO_LOGS = NETWORK_PATH / __LOGS
    PATH_TO_STATUS = NETWORK_PATH / __SYS_STATE

    # Files
    MILL_CONFIG = PATH_TO_CONFIG / __MILL_CONFIG_FILE_NAME
    WELLPLATE_LOCATION = PATH_TO_CONFIG / __WELLPLATE_CONFIG_FILE_NAME
    EPANDA_LOG = PATH_TO_LOGS / "ePANDA.log"

    # DB
    SQL_DB_PATH = NETWORK_PATH /"epanda_prod.db"
    ## Validate that all paths exist and create them if they don't
    for path in [
        PATH_TO_CODE,
        PATH_TO_SYSTEM_STATE,
        PATH_TO_CONFIG,
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
    MILL_CONFIG,
    WELLPLATE_LOCATION,
    EPANDA_LOG,
]:
    file_path = Path(PATH_TO_SYSTEM_STATE / file)
    if not file_path.exists():
        # print(f"Creating {file_path}")
        file_path.touch()
        print(f"Created {file_path}")

## Rename existing log file if it exists with timestamp
# if EPANDA_LOG.exists():
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     new_name = EPANDA_LOG.with_name(f"ePANDA_{timestamp}.log")
#     EPANDA_LOG.rename(new_name)
#     print(f"Renamed {EPANDA_LOG} to {new_name}")

# ## Create new log file
# EPANDA_LOG.touch()
# print(f"Created {EPANDA_LOG}")
