"""
Configuration testing utility for PANDA-BEAR

This file provides utilities for testing with temporary configurations.
It can be used both in test fixtures and individual tests.
"""

import os
import tempfile
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional, Union


class ConfigTestHelper:
    """Helper class for managing test configurations"""

    @staticmethod
    def create_test_config(config_content: Union[str, Dict, ConfigParser]) -> str:
        """
        Creates a temporary test configuration file

        Args:
            config_content: String content, dictionary or ConfigParser object
                            representing the configuration

        Returns:
            Path to the temporary config file
        """
        # Create a temporary config file
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".ini", prefix="panda_test_config_"
        )
        os.close(temp_fd)

        # Write configuration content
        if isinstance(config_content, str):
            with open(temp_path, "w") as f:
                f.write(config_content)
        elif isinstance(config_content, dict):
            config = ConfigParser()
            for section, values in config_content.items():
                if section not in config:
                    config[section] = {}
                for key, value in values.items():
                    config[section][key] = str(value)
            with open(temp_path, "w") as f:
                config.write(f)
        elif isinstance(config_content, ConfigParser):
            with open(temp_path, "w") as f:
                config_content.write(f)
        else:
            raise TypeError(
                "config_content must be a string, dictionary, or ConfigParser"
            )

        return temp_path

    @staticmethod
    def setup_test_environment(config_path: str):
        """
        Sets up the testing environment to use the provided config file

        Args:
            config_path: Path to the configuration file
        """  # Set environment variables for testing
        os.environ["PANDA_TESTING_CONFIG_PATH"] = config_path
        os.environ["PANDA_TESTING_MODE"] = "1"
        os.environ["PANDA_SDL_CONFIG_PATH"] = config_path

        # Ensure the config cache is cleared
        try:
            # Import here to avoid import cycles
            from shared_utilities.config.config_tools import reload_config

            # Use reload_config which internally clears any cached config
            reload_config()
        except Exception as e:
            print(f"Warning: Failed to clear config cache: {e}")

    @staticmethod
    def cleanup_test_environment(
        config_path: str, original_env: Optional[Dict[str, str]] = None
    ):
        """
        Cleans up the test environment and restores original settings

        Args:
            config_path: Path to the temporary config file
            original_env: Dictionary of original environment variables to restore
        """
        # Remove the temporary file if it exists
        if config_path and Path(config_path).exists():
            try:
                os.unlink(config_path)
            except OSError as e:
                print(f"Warning: Failed to remove temporary config file: {e}")

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
            if var not in (original_env or {}) and var in os.environ:
                del os.environ[var]

        # Clear config cache again
        try:
            from shared_utilities.config.config_tools import reload_config

            # Use reload_config to clear the cache and reload
            reload_config()
        except Exception as e:
            print(f"Warning: Failed to clear config cache: {e}")


@contextmanager
def temporary_config(config_content: Union[str, Dict, ConfigParser]):
    """
    Context manager for testing with a temporary configuration

    Args:
        config_content: Configuration content as string, dict or ConfigParser

    Yields:
        Path to the temporary config file
    """
    # Store original environment
    original_env = {}
    env_vars_to_store = [
        "PANDA_SDL_CONFIG_PATH",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
    ]
    for var in env_vars_to_store:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create temporary config
    temp_path = ConfigTestHelper.create_test_config(config_content)

    # Set up test environment
    ConfigTestHelper.setup_test_environment(temp_path)

    try:
        # Yield control to the caller
        yield temp_path
    finally:
        # Clean up regardless of exceptions
        ConfigTestHelper.cleanup_test_environment(temp_path, original_env)


# Example usage in a test:
"""
def test_some_feature():
    test_config = '''
    [PANDA]
    version = 2.0
    unit_id = 99
    
    [OPTIONS]
    testing = True
    '''
    
    with temporary_config(test_config) as config_path:
        # Now all calls to read_config() will use this temporary config
        from shared_utilities.config.config_tools import read_config
        config = read_config()
        assert config["PANDA"]["unit_id"] == "99"
"""
