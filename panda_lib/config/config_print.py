"""config test, read back the config file and interpret the paths"""

from configparser import ConfigParser
from pathlib import Path

# Read the config file
CONFIG_FILE = "./panda_lib/config/panda_sdl_config.ini"
config = ConfigParser()
config.read(CONFIG_FILE)


local_dir = Path(__file__).parent.parent
config.set("PATHS_GENERAL", "local_dir", str(local_dir))
config.write(open(CONFIG_FILE, "w", encoding="utf-8"))
config.read(CONFIG_FILE)

# Print the config file values
for section in config.sections():
    print(f"[{section}]")
    for key, value in config.items(section):

        # Handle None or blank values
        if value in [None, "", "None"]:
            print(f"{key} = None")
            continue

        if "dir" in key or "path" in key:
            try:
                # Check if the path exists
                assert Path(value).exists()
            except AssertionError:
                print(f"{key} = Path does not exist: {value}")
                continue

            # Generate complete path
            complete_path = Path(value).resolve()
            print(f"{key} = {complete_path}")

        else:
            print(f"{key} = {value}")
    print()
