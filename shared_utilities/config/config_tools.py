"""Utilities for setting and reading the configuration files"""

import logging
import os
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import find_dotenv, load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for config to avoid repeated disk reads
_config_cache = None


def get_env_var(env_var_name: str, default: str = None) -> Optional[str]:
    """Returns the value of an environment variable.

    Args:
        env_var_name: Name of the environment variable
        default: Default value if variable is not found

    Returns:
        Value of the environment variable or default
    """
    # Try to find .env file if not already loaded
    if not os.getenv("DOTENV_LOADED"):
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path)
            os.environ["DOTENV_LOADED"] = "True"
            logger.info(f"Loaded environment from {dotenv_path}")
        else:
            # Fallback - try relative to repo path
            repo_path = get_repo_path()
            possible_paths = [
                repo_path / ".env",
                repo_path.parent / ".env",
                Path.home() / ".panda_env",
            ]

            for path in possible_paths:
                if path.exists():
                    load_dotenv(path)
                    os.environ["DOTENV_LOADED"] = "True"
                    logger.info(f"Loaded environment from {path}")
                    break

    return os.getenv(env_var_name, default)


def get_repo_path() -> Path:
    """Returns the path of the repository."""
    current_file = Path(__file__).resolve()
    repo_path = current_file.parent.parent.parent
    return repo_path


def validate_config_path(config_path: str) -> bool:
    """Validates that the config path exists and is accessible.

    Args:
        config_path: Path to the configuration file

    Returns:
        True if valid, False otherwise

    Raises:
        FileNotFoundError: If config file doesn't exist
        PermissionError: If config file can't be accessed
    """
    if not config_path:
        raise FileNotFoundError("Configuration file path not specified.")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration path is not a file: {config_path}")
    if not os.access(config_path, os.R_OK):
        raise PermissionError(f"Configuration file is not readable: {config_path}")
    if not os.access(config_path, os.W_OK):
        raise PermissionError(f"Configuration file is not writable: {config_path}")
    return True


def is_testing_mode() -> bool:
    """Check if we're running in testing mode based on environment variables"""
    return (
        os.getenv("PANDA_TESTING_MODE") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )


def get_config_path() -> str:
    """Get the appropriate config path based on environment"""
    # First check for specific test config path
    if is_testing_mode():
        test_config_path = os.getenv("PANDA_TESTING_CONFIG_PATH")
        if test_config_path and os.path.exists(test_config_path):
            return test_config_path

    # Otherwise use the standard config path
    return get_env_var(
        "PANDA_SDL_CONFIG_PATH",
        default=str(get_repo_path() / "config" / "settings.ini"),
    )


@lru_cache(maxsize=1)
def read_config() -> ConfigParser:
    """Reads a configuration file with caching.

    Returns:
        ConfigParser object with loaded configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        PermissionError: If config file can't be accessed
    """
    global _config_cache

    config_path = get_config_path()

    # Only reload if config has changed or not loaded
    if _config_cache is None or not hasattr(_config_cache, "last_modified"):
        validate_config_path(config_path)
        config = ConfigParser()
        config.read(config_path)

        # Store last modified time for cache invalidation
        config.last_modified = os.path.getmtime(config_path)
        _config_cache = config
    else:
        # Check if file has been modified
        current_mtime = os.path.getmtime(config_path)
        if current_mtime > _config_cache.last_modified:
            config = ConfigParser()
            config.read(config_path)
            config.last_modified = current_mtime
            _config_cache = config

    return _config_cache


def reload_config() -> None:
    """Reloads the configuration file and clears the cache."""
    global _config_cache
    _config_cache = None
    read_config.cache_clear()
    read_config()
    logger.info("Configuration reloaded.")


def read_config_value(
    section: str, key: str, default: Any = None, fallback_section: str = None
) -> Any:
    """Reads a value from the configuration file with fallback options.

    Args:
        section: Configuration section
        key: Configuration key
        default: Default value if key not found
        fallback_section: Alternative section to check if key not in primary section

    Returns:
        Configuration value or default
    """
    config = read_config()

    try:
        value = config.get(section, key)
    except (ConfigParserError, KeyError):
        if fallback_section:
            try:
                return config.get(fallback_section, key)
            except (ConfigParserError, KeyError):
                pass
        return default

    # Convert to appropriate type
    if value.lower() in ("true", "1"):
        return True
    elif value.lower() in ("false", "0"):
        return False
    elif value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        pass
    return value
    # If all else fails, return the string value


def write_config_value(section: str, key: str, value: str) -> None:
    """Writes a value to the configuration file.

    Args:
        section: Configuration section
        key: Configuration key
        value: Value to write
    """
    config_path = get_env_var("PANDA_SDL_CONFIG_PATH")
    validate_config_path(config_path)

    config = read_config()

    # Ensure section exists
    if not config.has_section(section):
        config.add_section(section)

    config.set(section, key, str(value))

    with open(config_path, "w", encoding="utf-8") as config_file:
        config.write(config_file)

    # Invalidate cache
    global _config_cache
    _config_cache = None
    read_config.cache_clear()


def get_config_boolean(section: str, key: str, default: bool = False) -> bool:
    """Gets a boolean value from config with proper type conversion.

    Args:
        section: Configuration section
        key: Configuration key
        default: Default value if key not found

    Returns:
        Boolean configuration value
    """
    config = read_config()
    try:
        return config.getboolean(section, key)
    except (ConfigParserError, KeyError):
        return default


def get_config_int(section: str, key: str, default: int = 0) -> int:
    """Gets an integer value from config with proper type conversion.

    Args:
        section: Configuration section
        key: Configuration key
        default: Default value if key not found

    Returns:
        Integer configuration value
    """
    config = read_config()
    try:
        return config.getint(section, key)
    except (ConfigParserError, KeyError):
        return default


def get_config_float(section: str, key: str, default: float = 0.0) -> float:
    """Gets a float value from config with proper type conversion.

    Args:
        section: Configuration section
        key: Configuration key
        default: Default value if key not found

    Returns:
        Float configuration value
    """
    config = read_config()
    try:
        return config.getfloat(section, key)
    except (ConfigParserError, KeyError):
        return default


def read_testing_config() -> bool:
    """Reads the testing configuration flag.

    Returns:
        True if testing mode is enabled, False otherwise
    """
    # Always return True if environment indicates we're in testing mode
    if is_testing_mode():
        return True

    try:
        return get_config_boolean("OPTIONS", "testing", default=False)
    except (FileNotFoundError, PermissionError, ConfigParserError) as e:
        logger.warning(f"Failed to read testing config: {e}")
        return False


def write_testing_config(enable_testing: bool) -> None:
    """Sets the testing configuration flag.

    Args:
        enable_testing: Whether to enable testing mode
    """
    try:
        write_config_value("OPTIONS", "testing", str(enable_testing))
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to write testing config: {e}")
        raise


# Rest of functions can use the new helpers
def read_logging_dir() -> str:
    """Reads the logging directory from the configuration file."""
    section = "TESTING" if read_testing_config() else "PRODUCTION"
    return read_config_value(
        section, "logging_dir", default=str(get_repo_path() / "logs")
    )


def read_data_dir() -> str:
    """Reads the data directory from the configuration file."""
    section = "TESTING" if read_testing_config() else "PRODUCTION"
    return read_config_value(section, "data_dir", default=str(get_repo_path() / "data"))


def read_camera_type() -> Optional[str]:
    """Reads the camera type from the configuration file.

    Returns:
        str: The camera type ('flir' or 'webcam')
    """
    return read_config_value("CAMERA", "camera_type", default="flir")


def read_webcam_settings() -> Tuple[int, Tuple[int, int]]:
    """Reads webcam settings from the configuration file.

    Returns:
        tuple: (webcam_id, resolution_width, resolution_height)
    """
    webcam_id = get_config_int("CAMERA", "webcam_id", default=0)
    width = get_config_int("CAMERA", "webcam_resolution_width", default=1280)
    height = get_config_int("CAMERA", "webcam_resolution_height", default=720)

    return webcam_id, (width, height)


def get_all_section_settings(section: str) -> Dict[str, str]:
    """Gets all key-value pairs from a configuration section.

    Args:
        section: Name of the configuration section

    Returns:
        Dictionary of all settings in the section
    """
    config = read_config()
    try:
        if config.has_section(section):
            return dict(config[section])
        return {}
    except (ConfigParserError, KeyError):
        return {}


def test():
    """Tests the functions in this module."""
    print(f"Repository path: {get_repo_path()}")
    print(f"Testing mode: {read_testing_config()}")

    # Test write and read
    write_testing_config(True)
    print(f"Testing mode after enable: {read_testing_config()}")

    write_testing_config(False)
    print(f"Testing mode after disable: {read_testing_config()}")

    # Restore testing mode to original state
    write_testing_config(False)

    # Test new functions
    print(f"Logging directory: {read_logging_dir()}")
    print(f"Data directory: {read_data_dir()}")
    print(f"Camera type: {read_camera_type()}")
    print(f"Webcam settings: {read_webcam_settings()}")


if __name__ == "__main__":
    test()
