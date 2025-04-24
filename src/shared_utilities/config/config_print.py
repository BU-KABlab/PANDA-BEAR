"""config test, read back the config file and interpret the paths"""

import os
from configparser import ConfigParser
from pathlib import Path

from dotenv import load_dotenv

env_found = load_dotenv()

if not env_found:
    # print("No .env file found. Please create one with the required environment variables.")
    # make_for_user = input("Create a new .env file? (y/n): ")
    # if make_for_user.lower() == "y":
    #     with open(".env", "w") as f:
    #         f.write("PANDA_SDL_CONFIG_PATH=./panda_lib/config/config.ini\n")
    #         f.write("# Temp DB for pytest\nTEMP_DB='0'\n")

    # else:
    raise FileNotFoundError(
        "No .env file found. Please create one with the required environment variables:" \
        "\nPANDA_SDL_CONFIG_PATH=./panda_lib/config/config.ini\nTEMP_DB='0'"
    )


from .config_tools import is_testing_mode  # noqa: E402


def load_default_config():
    """Load the default configuration file."""
    config = ConfigParser()
    config.read("./panda_lib/config/default_config.ini")
    return config


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
            value = value.split(";", 1)[0].strip()
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

    if not is_testing_mode():  # Skip if we're running in testing mode
        input("\nPress Enter to continue...\n\n")


def resolve_config_paths():
    # Read the config file
    CONFIG_FILE = os.getenv("PANDA_SDL_CONFIG_PATH")
    if not CONFIG_FILE or not Path(CONFIG_FILE).exists():
        print("PANDA_SDL_CONFIG_PATH environment variable not set or config file not found.")
        print("Please refer to the documentation for instructions on how to set up both the .env and .ini file.")
        print("https://github.com/BU-KABlab/PANDA-BEAR/blob/packaing/documentation/installation.md#env-file")
        exit()

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

        print(
            "Default config file generated. Please edit the config file and run again."
        )

    # Check that the config file has all sections and keys as the default config file
    default_config = load_default_config()
    for section in default_config.sections():
        if not config.has_section(section):
            print(f"Missing section: {section} in config file, creating it...")
            config.add_section(section)
            for key, value in default_config.items(section):
                config.set(section, key, value)
            continue
        for key, value in default_config.items(section):
            if not config.has_option(section, key):
                print(
                    f"Missing key: {key} in section: {section} in config file. Creating it..."
                )
                config.set(section, key, value)
                continue
            # Not checking the value of the key, just that it exists

    # Skip validation and interactive prompts if we're running in testing mode
    if is_testing_mode():
        # Just write the config file and return
        config.write(open(CONFIG_FILE, "w", encoding="utf-8"))
        return

    # Print the config file values
    for section in config.sections():
        for key, value in config.items(section):
            value = value.split(";", 1)[0].strip()  # Remove comments
            # Check that the db_address for both testing and production are valid
            if "db_address" in key:
                try:
                    if value not in [None, "", "None", '""']:
                        # Check if the path exists
                        assert Path(value).resolve().exists()
                    else:
                        raise AssertionError
                except AssertionError:
                    print(f"{key} = Path does not exist: {value}")
                    generate_blank_db = input("Create the default database? (y/n): ")
                    if generate_blank_db.lower() == "y":
                        # from shutil import copyfile

                        # copyfile("./panda_lib/config/template.db", ".")
                        from panda_lib_db.db_setup import setup_database, return_sql_dump_file
                        setup_database(
                            db_path=value,
                            sql_dump=return_sql_dump_file(),
                            drop_existing=True,
                        )
                    else:
                        raise FileNotFoundError

            # Handle None or blank values
            if value in [None, "", "None"]:
                continue

            if "dir" in key or "path" in key:
                # Check if the path exists
                if not Path(value).resolve().exists():
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
