"""
Configuration interface for PANDA-BEAR

This module provides a unified interface for accessing configuration settings
across the application, with built-in support for testing environments.

PENDING IMPLEMENTATION
"""

import logging
import os
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration instance
_config_instance = None


class ConfigInterface:
    """Interface for configuration access that can be easily replaced/mocked in tests"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration interface

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = ConfigParser()
        self._config_path = None

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from specified path

        Args:
            config_path: Path to the configuration file

        Returns:
            True if successful, False otherwise
        """
        if not config_path or not os.path.exists(config_path):
            logger.warning(f"Configuration file not found: {config_path}")
            return False

        try:
            self.config.read(config_path)
            self._config_path = config_path
            logger.debug(f"Loaded configuration from {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def get_config_path(self) -> Optional[str]:
        """
        Get the path of the currently loaded configuration file

        Returns:
            Path to the configuration file or None if not loaded
        """
        return self._config_path

    def get(self, section: str, key: str, default: Any = None) -> str:
        """
        Get string value from configuration

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value as string
        """
        return self.config.get(section, key, fallback=default)

    def get_int(
        self, section: str, key: str, default: Optional[int] = None
    ) -> Optional[int]:
        """
        Get integer value from configuration

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value as integer
        """
        try:
            return self.config.getint(section, key, fallback=default)
        except (ValueError, TypeError):
            logger.debug(
                f"Failed to get int value for {section}.{key}, returning default"
            )
            return default

    def get_float(
        self, section: str, key: str, default: Optional[float] = None
    ) -> Optional[float]:
        """
        Get float value from configuration

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value as float
        """
        try:
            return self.config.getfloat(section, key, fallback=default)
        except (ValueError, TypeError):
            logger.debug(
                f"Failed to get float value for {section}.{key}, returning default"
            )
            return default

    def get_bool(
        self, section: str, key: str, default: Optional[bool] = None
    ) -> Optional[bool]:
        """
        Get boolean value from configuration

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value as boolean
        """
        try:
            return self.config.getboolean(section, key, fallback=default)
        except (ValueError, TypeError):
            logger.debug(
                f"Failed to get bool value for {section}.{key}, returning default"
            )
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = str(value)

    def has_section(self, section: str) -> bool:
        """
        Check if section exists in configuration

        Args:
            section: Section name

        Returns:
            True if section exists, False otherwise
        """
        return self.config.has_section(section)

    def has_option(self, section: str, key: str) -> bool:
        """
        Check if option exists in configuration section

        Args:
            section: Section name
            key: Option name

        Returns:
            True if option exists, False otherwise
        """
        return self.config.has_option(section, key)

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """
        Convert configuration to dictionary

        Returns:
            Dictionary representation of configuration
        """
        result = {}
        for section in self.config.sections():
            result[section] = {}
            for key, value in self.config.items(section):
                result[section][key] = value
        return result

    def from_dict(self, config_dict: Dict[str, Dict[str, Any]]) -> None:
        """
        Load configuration from dictionary

        Args:
            config_dict: Dictionary containing configuration
        """
        for section, options in config_dict.items():
            if section not in self.config:
                self.config[section] = {}
            for key, value in options.items():
                self.config[section][key] = str(value)


def get_repo_path() -> Path:
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent.parent.parent
    return repo_path


def is_testing_mode() -> bool:
    """Check if we're running in testing mode based on environment variables"""
    return (
        os.getenv("PANDA_TESTING_MODE") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )


def get_config() -> ConfigInterface:
    """
    Get the global configuration instance

    Returns:
        ConfigInterface instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = ConfigInterface()

        # Determine appropriate config path based on environment
        if is_testing_mode():
            # First check for specific test config path
            test_config_path = os.getenv("PANDA_TESTING_CONFIG_PATH")
            if test_config_path and os.path.exists(test_config_path):
                logger.debug(f"Loading test configuration from {test_config_path}")
                _config_instance.load_config(test_config_path)
                return _config_instance

        # Otherwise use the standard config path
        config_path = os.getenv(
            "PANDA_SDL_CONFIG_PATH", str(get_repo_path() / "panda_sdl_config.ini")
        )

        if os.path.exists(config_path):
            logger.debug(f"Loading configuration from {config_path}")
            _config_instance.load_config(config_path)
        else:
            logger.warning(f"Configuration file not found at {config_path}")

    return _config_instance


def reset_config() -> None:
    """
    Reset the global configuration instance
    This is primarily used for testing
    """
    global _config_instance
    _config_instance = None
    logger.debug("Configuration instance reset")


def create_test_config(
    config_content: Union[str, Dict, ConfigParser],
) -> ConfigInterface:
    """
    Create a test configuration instance

    Args:
        config_content: Configuration content (string, dictionary, or ConfigParser)

    Returns:
        ConfigInterface instance with test configuration
    """
    config = ConfigInterface()

    if isinstance(config_content, str):
        # Create temporary file with content
        import tempfile

        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".ini", prefix="panda_test_config_"
        )
        os.close(temp_fd)

        with open(temp_path, "w") as f:
            f.write(config_content)

        config.load_config(temp_path)

        # Clean up temp file
        os.unlink(temp_path)

    elif isinstance(config_content, dict):
        config.from_dict(config_content)

    elif isinstance(config_content, ConfigParser):
        config.config = config_content

    else:
        raise TypeError("config_content must be string, dictionary, or ConfigParser")

    return config
