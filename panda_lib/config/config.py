"""The home of all project specific strings and values that are 
better to be set in one place than to be scattered around the code."""

from configparser import ConfigParser
from pathlib import Path
import sqlite3

from panda_lib.config.config_tools import get_env_var, read_config


configuration_path = get_env_var("PANDA_SDL_CONFIG_PATH")
config = read_config()

def get_repo_path():
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent
    return repo_path


## Define local repository path - will also be used during testing
LOCAL_REPO_PATH = Path(__file__).parents[2]

## Testing flag
# testing.txt is the only place to change the mode besides from the main menue
# The file is created if it does not exist

## Flag to use only local paths - can be changed while running the program
TESTING_MODE_ACTIVE = config.getboolean("OPTIONS", "testing")
try:
    TESTING_DIRECTORY = config.get("TESTING","testing_dir")

    if TESTING_DIRECTORY in [None, "",'None']:
        raise KeyError

    TESTING_DIRECTORY = Path(TESTING_DIRECTORY)

except KeyError:
    TESTING_DIRECTORY = LOCAL_REPO_PATH
## Define external path for data, logs, and system state

if not TESTING_MODE_ACTIVE:
    try:
        PRODUCTION_DIRECTORY = config.get("PRODUCTION","production_dir")

        if PRODUCTION_DIRECTORY in [None, "",'None']:
            raise KeyError

        PRODUCTION_DIRECTORY = Path(PRODUCTION_DIRECTORY)
    except KeyError:
        print("PANDA_SDL_EXTERNAL_PATH environment variable not set.")
        print("Switching to testing mode")
        config.set("OPTIONS", "testing", "True")
        config.write(open(configuration_path, "w",encoding="utf-8"))
        config.read(configuration_path)
        TESTING_MODE_ACTIVE = True


## FLIR Camera related - must be a python 3.6 environment
try:
    PYTHON_360_PATH = config.get("GENERAL", "python_360_path")

    if PYTHON_360_PATH in [None, "",'None']:
        raise KeyError

    PYTHON_360_PATH = Path(PYTHON_360_PATH)
except KeyError as e:
    raise ValueError("PANDA_SDL_PYTHON_360_PATH environment variable not set.") from e

CAMERA_SCRIPT_PATH = Path(LOCAL_REPO_PATH / "panda_lib" / "flir_camera" / "camera.py")

## Build complete paths for each project directory or file
if TESTING_MODE_ACTIVE:
    # Directories

    # DB
    try:
        SQL_DB_PATH = config.get("TESTING","testing_db_address")

        if SQL_DB_PATH in [None, "",'None']:
            raise KeyError

        SQL_DB_PATH = Path(SQL_DB_PATH)
    except KeyError:
        print("PANDA_SDL_TESTING_DB_PATH environment variable not set in .env file.")
        print("Using default path")
        SQL_DB_PATH = LOCAL_REPO_PATH / "test.db"

    # Test that the db exists, and if not create it using the included test_db.sql
    if not SQL_DB_PATH.exists():
        Path(SQL_DB_PATH).with_suffix(".db").touch()
        conn = sqlite3.connect(SQL_DB_PATH)
        with open(LOCAL_REPO_PATH / "template_db.sql", "r",encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

else:
    # DB
    try:
        SQL_DB_PATH = config.get("PRODUCTION","production_db_address")

        if SQL_DB_PATH in [None, "",'None']:
            raise KeyError

        SQL_DB_PATH = Path(SQL_DB_PATH)

    except KeyError:
        print("PANDA_SDL_PRODUCTION_DB_PATH environment variable not set in .env file.")
        print("Using a local db")
        SQL_DB_PATH = LOCAL_REPO_PATH / "prod.db"
        if not Path(SQL_DB_PATH).with_suffix(".db").exists():
            Path(SQL_DB_PATH).with_suffix(".db").touch()
            conn = sqlite3.connect(SQL_DB_PATH)
            with open(LOCAL_REPO_PATH / "template_db.sql", "r",encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.close()

    # Test that a connection can be made to the db. If not raise exception
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        conn.close()
    except sqlite3.Error as e:
        raise f"Error connecting to database: {e}" from e
