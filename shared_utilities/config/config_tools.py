"""Utilities for setting and reading the configuration files"""

import os
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from pathlib import Path

from dotenv import load_dotenv


def get_env_var(env_var_name: str) -> str:
    """Returns the value of an environment variable."""
    load_dotenv()
    return os.getenv(env_var_name)


def get_repo_path():
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent
    return repo_path


def read_config_value(section: str, key: str) -> str:
    """Reads a value from the configuration file."""
    config = read_config()
    return config.get(section, key)


def write_config_value(section: str, key: str, value: str):
    """Writes a value to the configuration file."""
    config_path = get_env_var("PANDA_SDL_CONFIG_PATH")
    config = ConfigParser()
    config.read(config_path)
    config.set(section, key, value)
    with open(config_path, "w", encoding="utf-8") as config_file:
        config.write(config_file)


def read_testing_config():
    """Reads the testing configuration file."""
    try:
        config_path = get_env_var("PANDA_SDL_CONFIG_PATH")
        config = ConfigParser()
        config.read(config_path)
        return config.getboolean("OPTIONS", "testing")
    except ConfigParserError:
        return False


def write_testing_config(enable_testing: bool):
    """Writes the testing configuration file."""
    config_path = get_env_var("PANDA_SDL_CONFIG_PATH")
    config = ConfigParser()
    config.read(config_path)
    config.set("OPTIONS", "testing", str(enable_testing))
    with open(config_path, "w", encoding="utf-8") as config_file:
        config.write(config_file)


def read_config() -> ConfigParser:
    """Reads a configuration file."""
    config_path = get_env_var("PANDA_SDL_CONFIG_PATH")
    config = ConfigParser()
    config.read(config_path)
    return config


def read_logging_dir() -> str:
    """Reads the logging directory from the configuration file."""
    config = read_config()
    if read_testing_config():
        return config.get("TESTING", "logging_dir")
    else:
        return config.get("PRODUCTION", "logging_dir")


def read_data_dir() -> str:
    """Reads the data directory from the configuration file."""
    config = read_config()
    if read_testing_config():
        return config.get("TESTING", "data_dir")
    else:
        return config.get("PRODUCTION", "data_dir")


def read_camera_type() -> str:
    """Reads the camera type from the configuration file.

    Returns:
        str: The camera type ('flir' or 'webcam')
    """
    config = read_config()
    try:
        return config.get("CAMERA", "camera_type")
    except (ConfigParserError, KeyError):
        # Default to flir if not specified
        return "flir"


def read_webcam_settings() -> tuple:
    """Reads webcam settings from the configuration file.

    Returns:
        tuple: (webcam_id, resolution_width, resolution_height)
    """
    config = read_config()
    try:
        webcam_id = config.getint("CAMERA", "webcam_id")
    except (ConfigParserError, KeyError):
        webcam_id = 0

    try:
        width = config.getint("CAMERA", "webcam_resolution_width")
    except (ConfigParserError, KeyError):
        width = 1280

    try:
        height = config.getint("CAMERA", "webcam_resolution_height")
    except (ConfigParserError, KeyError):
        height = 720

    return webcam_id, (width, height)


def test():
    """Tests the functions in this module."""
    print(get_repo_path())
    print(read_testing_config())
    write_testing_config(True)
    print(read_testing_config())
    write_testing_config(False)
    print(read_testing_config())


if __name__ == "__main__":
    test()
