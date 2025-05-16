"""
Test configuration environment manager
This module provides utilities for creating, managing, and cleaning up
test configuration environments including .env and .ini files
"""

import os
import tempfile
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Tuple

# Get the template paths
CONFIG_DIR = Path(__file__).parent
ENV_TEMPLATE_PATH = CONFIG_DIR / "test_env_template.env"


def create_test_env_file(config_path: str) -> str:
    """
    Create a temporary .env file for testing based on the template

    Args:
        config_path: Path to the config file that will be referenced in the .env

    Returns:
        Path to the created .env file
    """
    # Create a temporary file for the .env
    temp_fd, temp_path = tempfile.mkstemp(suffix=".env", prefix="panda_test_env_")
    os.close(temp_fd)

    # Read the template
    with open(ENV_TEMPLATE_PATH, "r") as template_file:
        env_content = template_file.read()

    # Replace variables
    env_content = env_content.replace("${TEST_CONFIG_PATH}", config_path)

    # Write to the temporary file
    with open(temp_path, "w") as env_file:
        env_file.write(env_content)

    return temp_path


def setup_test_environment() -> Tuple[str, str, Dict[str, str]]:
    """
    Set up a complete test environment with .ini and .env files

    Returns:
        Tuple containing (config_path, env_path, original_env)
    """
    # Store original environment variables
    original_env = {}
    env_vars_to_store = [
        "PANDA_SDL_CONFIG_PATH",
        "TEMP_DB",
        "PANDA_UNIT_ID",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "DOTENV_LOADED",
    ]

    for var in env_vars_to_store:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create a temporary config file
    temp_fd, config_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)

    # Write default testing configuration
    config = ConfigParser()

    # Load default config sections from shared utilities
    default_config_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "shared_utilities"
        / "config"
        / "default_config.ini"
    )
    if default_config_path.exists():
        config.read(default_config_path)

    # Override with test-specific values
    if not config.has_section("PANDA"):
        config.add_section("PANDA")
    config.set("PANDA", "version", "2.0")
    config.set("PANDA", "unit_id", "99")
    config.set("PANDA", "unit_name", "TestUnit")

    if not config.has_section("OPTIONS"):
        config.add_section("OPTIONS")
    config.set("OPTIONS", "testing", "True")

    if not config.has_section("TESTING"):
        config.add_section("TESTING")
    config.set("TESTING", "testing_db_type", "sqlite")
    config.set("TESTING", "testing_db_address", "temp.db")

    if not config.has_section("PIPETTE"):
        config.add_section("PIPETTE")
    config.set("PIPETTE", "pipette_type", "OT2")

    # Write the config file
    with open(config_path, "w") as f:
        config.write(f)

    # Create a .env file that points to this config
    env_path = create_test_env_file(config_path)

    # Set environment variables for testing
    os.environ["PANDA_TESTING_CONFIG_PATH"] = config_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_UNIT_ID"] = "99"
    os.environ["TEMP_DB"] = "1"
    os.environ["PANDA_SDL_CONFIG_PATH"] = config_path
    os.environ["DOTENV_LOADED"] = "True"

    return config_path, env_path, original_env


def cleanup_test_environment(
    config_path: str, env_path: str, original_env: Dict[str, str]
):
    """
    Clean up the test environment and restore original settings

    Args:
        config_path: Path to the config file to remove
        env_path: Path to the .env file to remove
        original_env: Dictionary of original environment variables to restore
    """
    # Remove temporary files
    for path in [config_path, env_path]:
        if path and Path(path).exists():
            try:
                os.unlink(path)
            except OSError as e:
                print(f"Warning: Failed to remove temporary file {path}: {e}")

    # Restore original environment variables
    for var, value in original_env.items():
        os.environ[var] = value

    # Remove testing environment variables if not in original_env
    test_env_vars = [
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_SDL_CONFIG_PATH",
        "TEMP_DB",
        "PANDA_UNIT_ID",
        "DOTENV_LOADED",
    ]

    for var in test_env_vars:
        if var not in original_env and var in os.environ:
            del os.environ[var]

    # Clear config cache
    try:
        from shared_utilities.config.config_tools import reload_config

        reload_config()
    except (ImportError, AttributeError) as e:
        print(f"Warning: Failed to clear config cache: {e}")
