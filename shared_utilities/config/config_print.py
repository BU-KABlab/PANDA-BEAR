"""config test, read back the config file and interpret the paths"""

import os
from configparser import ConfigParser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def print_config_values():
    # Read the config file
    CONFIG_FILE = os.getenv("PANDA_SDL_CONFIG_PATH")
    config = ConfigParser()
    config.read(CONFIG_FILE)

    local_dir = Path(__file__).parent.parent
    config.set("GENERAL", "local_dir", str(local_dir))
    config.write(open(CONFIG_FILE, "w", encoding="utf-8"))
    config.read(CONFIG_FILE)

    # Print the config file values
    print(f"\n\nConfig file: {CONFIG_FILE}\n")
    for section in config.sections():
        print(f"[{section}]")
        for key, value in config.items(section):
            # Handle None or blank values
            if value in [None, "", "None"]:
                print(f"{key} = None")
                continue

            if "dir" in key or "path" in key:
                if value not in [None, "", "None", '""']:
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

    input("\nPress Enter to continue...\n\n")


def resolve_config_paths():
    # Read the config file
    CONFIG_FILE = os.getenv("PANDA_SDL_CONFIG_PATH")
    config = ConfigParser()

    try:
        config.read(CONFIG_FILE)
    except FileNotFoundError:
        print("Config file not found. Generating defualt config file.")

        # Generate default config file from default_config.ini
        default_config = ConfigParser()
        default_config.read("./panda_lib/config/default_config.ini")
        with open(CONFIG_FILE, "w") as configfile:
            default_config.write(configfile)

        # Read the config file
        config.read(CONFIG_FILE)

    # Print the config file values
    for section in config.sections():
        for key, value in config.items(section):
            # Check that the db_address for both testing and production are valid
            if "db_address" in key:
                    try:
                        if value not in [None, "", "None", '""']:
                            # Check if the path exists
                            assert Path(value).exists()
                        else:
                            raise AssertionError
                    except AssertionError:
                        print(f"{key} = Path does not exist: {value}")
                        generate_blank_db = input("Use default template database? (y/n): ")
                        if generate_blank_db.lower() == "y":
                            from shutil import copyfile
                            copyfile("./panda_lib/config/template.db", ".")
                        else:
                            raise FileNotFoundError
            
            # Handle None or blank values
            if value in [None, "", "None"]:
                continue


            if "dir" in key or "path" in key:
                # Check if the path exists
                if not Path(value).exists():
                    print(f"{key} = Path does not exist: {value}")
                    create = input("Create the path? (y/n): ")
                    if create.lower() == "y":
                        Path(value).mkdir(parents=True, exist_ok=True)
                    else:
                        continue

                # Generate complete path
                complete_path = Path(value).resolve()
                config.set(section, key, str(complete_path))

    # Write the updated config file
    config.write(open(CONFIG_FILE, "w", encoding="utf-8"))


if __name__ == "__main__":
    print_config_values()
