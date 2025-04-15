"""Utilities for testing with configuration settings"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from .config_tools import read_config, reload_config


def setup_test_config(
    config_content: str, environment_vars: Optional[Dict[str, str]] = None
) -> str:
    """
    Creates a temporary test configuration file with the provided content.

    Args:
        config_content: The content to write to the config file
        environment_vars: Optional dictionary of environment variables to set

    Returns:
        Path to the temporary config file
    """
    # Create a temporary config file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)

    # Write the provided configuration content
    with open(temp_path, "w") as f:
        f.write(config_content)

    # Set environment variables for testing
    if environment_vars:
        for key, value in environment_vars.items():
            os.environ[key] = value

    # Always set these testing environment variables
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path

    # Clear any cached configuration
    read_config.cache_clear()
    reload_config()

    return temp_path


def teardown_test_config(
    config_path: str, original_env: Optional[Dict[str, str]] = None
) -> None:
    """
    Removes the temporary test configuration file and restores original environment.

    Args:
        config_path: Path to the temporary config file to remove
        original_env: Dictionary of original environment variables to restore
    """
    try:
        # Remove the temporary file
        if config_path and Path(config_path).exists():
            os.unlink(config_path)

        # Restore original environment variables
        if original_env:
            for var, value in original_env.items():
                os.environ[var] = value

        # Remove testing environment variables if not in original_env
        test_env_vars = [
            "PANDA_TESTING_CONFIG_PATH",
            "PANDA_TESTING_MODE",
            "PANDA_SDL_CONFIG_PATH",
        ]

        for var in test_env_vars:
            if var not in (original_env or {}):
                if var in os.environ:
                    del os.environ[var]

        # Clear any cached configuration
        read_config.cache_clear()
        reload_config()

    except (OSError, KeyError) as e:
        print(f"Error during test config cleanup: {e}")


def get_original_env() -> Dict[str, str]:
    """
    Store original environment variables that might be modified during testing.

    Returns:
        Dictionary of environment variables and their values
    """
    env_vars_to_store = [
        "PANDA_SDL_CONFIG_PATH",
        "TEMP_DB",
        "PANDA_UNIT_ID",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
    ]

    original_env = {}
    for var in env_vars_to_store:
        if var in os.environ:
            original_env[var] = os.environ[var]

    return original_env
