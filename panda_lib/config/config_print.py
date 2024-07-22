"""config test, read back the config file and interpret the paths"""

import os
from configparser import ConfigParser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main():
    # Read the config file
    CONFIG_FILE = os.getenv("PANDA_SDL_CONFIG_PATH")
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
                config.set(section, key, str(complete_path))

            else:
                print(f"{key} = {value}")
        print()

    # Write the updated config file
    config.write(open(CONFIG_FILE, "w", encoding="utf-8"))


def resolve_config_paths():
    # Read the config file
    CONFIG_FILE = "./panda_lib/config/panda_sdl_config.ini"
    config = ConfigParser()
    config.read(CONFIG_FILE)

    # Print the config file values
    for section in config.sections():
        for key, value in config.items(section):

            # Handle None or blank values
            if value in [None, "", "None"]:
                continue

            if "dir" in key or "path" in key:
                # Check if the path exists
                if not Path(value).exists():
                    continue

                # Generate complete path
                complete_path = Path(value).resolve()
                config.set(section, key, str(complete_path))

    # Write the updated config file
    config.write(open(CONFIG_FILE, "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
