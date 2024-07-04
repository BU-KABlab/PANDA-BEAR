"""Utilities for setting and reading the configuration files"""
from pathlib import Path
from configparser import ConfigParser

def get_repo_path():
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent
    return repo_path

def read_testing_config():
    """Reads the testing configuration file."""
    repo_path = get_repo_path()
    config_path = repo_path / "config" / "panda_sdl_config.ini"
    config = ConfigParser()
    config.read(config_path)
    return config.getboolean("OPTIONS", "testing")

def write_testing_config(enable_testing: bool):
    """Writes the testing configuration file."""
    repo_path = get_repo_path()
    config_path = repo_path / "config" / "panda_sdl_config.ini"
    config = ConfigParser()
    config.read(config_path)
    config.set("OPTIONS", "testing", str(enable_testing))
    with open(config_path, "w", encoding='utf-8') as config_file:
        config.write(config_file)
