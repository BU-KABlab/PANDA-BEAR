"""Utilities for setting and reading the configuration files"""
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
        f.write(str(value))
