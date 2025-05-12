"""
Configuration fixtures for testing
"""

import os
from typing import Any, Dict

import pytest

from src.shared_utilities.config.config_interface import (
    create_test_config,
    get_config,
    reset_config,
)


@pytest.fixture
def test_config():
    """
    Fixture providing a standard test configuration

    Returns:
        ConfigInterface instance with test configuration
    """
    # Create a test configuration with standard test values
    config = create_test_config(
        {
            "PANDA": {"version": "2.0", "unit_id": "99", "unit_name": "TestUnit"},
            "DEFAULTS": {
                "air_gap": "40.0",
                "drip_stop_volume": "5.0",
                "pipette_purge_volume": "20.0",
                "pumping_rate": "0.3",
            },
            "OPTIONS": {
                "testing": "True",
                "random_experiment_selection": "False",
                "use_slack": "False",
                "use_obs": "False",
                "precision": "6",
            },
            "MILL": {"port": "MOCK_PORT", "baudrate": "9600", "timeout": "10"},
            "TESTING": {
                "testing_dir": "tests/panda_lib",
                "testing_db_type": "sqlite",
                "testing_db_address": "temp.db",
            },
        }
    )

    return config


@pytest.fixture
def custom_test_config(request):
    """
    Fixture for creating a customized test configuration

    This fixture requires the test to specify a 'config_values' parameter with
    a dictionary of configuration values to override the defaults.

    Example:
        @pytest.mark.parametrize('custom_test_config', [
            {'PANDA': {'unit_id': '123'}, 'MILL': {'port': 'CUSTOM_PORT'}}
        ], indirect=True)
        def test_with_custom_config(custom_test_config):
            # The config now has unit_id=123 and port=CUSTOM_PORT
            assert custom_test_config.get('PANDA', 'unit_id') == '123'

    Returns:
        ConfigInterface instance with custom configuration
    """
    # Get the standard test configuration first
    config = create_test_config(
        {
            "PANDA": {"version": "2.0", "unit_id": "99", "unit_name": "TestUnit"},
            "OPTIONS": {"testing": "True"},
            "MILL": {"port": "MOCK_PORT"},
        }
    )

    # Apply custom overrides
    if hasattr(request, "param"):
        custom_values = request.param
        for section, options in custom_values.items():
            if section not in config.config:
                config.config[section] = {}
            for key, value in options.items():
                config.config[section][key] = str(value)

    return config


@pytest.fixture
def patch_global_config(test_config):
    """
    Fixture that temporarily replaces the global configuration with a test configuration

    This is useful for tests that call code which uses get_config() internally.

    Example:
        def test_function_that_uses_config(patch_global_config):
            # Now any call to get_config() will return the test config
            result = function_that_uses_config_internally()
            assert result == expected_value

    Yields:
        The test ConfigInterface instance
    """
    # Store original instance
    from src.shared_utilities.config.config_interface import _config_instance

    original_instance = _config_instance

    # Reset and mock the global config
    reset_config()
    from src.shared_utilities.config.config_interface import _config_instance

    _config_instance = test_config

    yield test_config

    # Restore original instance
    from src.shared_utilities.config.config_interface import _config_instance

    _config_instance = original_instance


@pytest.fixture
def temp_config_file():
    """
    Fixture that creates a temporary configuration file

    This fixture is useful when testing code that directly reads config files
    rather than using the ConfigInterface.

    Yields:
        Path to temporary configuration file
    """
    import tempfile

    # Create a temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)

    # Write standard test configuration
    with open(temp_path, "w") as f:
        f.write("""
[PANDA]
version = 2.0
unit_id = 99
unit_name = TestUnit

[OPTIONS]
testing = True

[MILL]
port = MOCK_PORT
baudrate = 9600

[TESTING]
testing_db_type = sqlite
testing_db_address = temp.db
""")

    # Store original environment variables
    original_env = {}
    for var in [
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Set environment variables for testing
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path

    # Reset any cached config
    reset_config()

    yield temp_path

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)

    # Restore original environment
    for var, value in original_env.items():
        os.environ[var] = value

    for var in [
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var not in original_env and var in os.environ:
            del os.environ[var]

    # Reset config again
    reset_config()


# Example of a fixture with context manager
@pytest.fixture
def with_config_values():
    """
    Factory fixture for temporarily setting configuration values

    This fixture returns a context manager that can be used to temporarily
    set configuration values for the duration of a test.

    Example:
        def test_with_custom_values(with_config_values):
            with with_config_values({'PANDA': {'unit_id': '888'}}):
                # Inside this block, get_config().get('PANDA', 'unit_id') == '888'
                assert get_config().get('PANDA', 'unit_id') == '888'

            # Outside the block, the original values are restored

    Returns:
        Context manager for temporarily setting config values
    """
    from contextlib import contextmanager

    @contextmanager
    def _with_values(config_dict: Dict[str, Dict[str, Any]]):
        # Get the current configuration
        config = get_config()

        # Store original values
        original_values = {}
        for section, options in config_dict.items():
            if section not in original_values:
                original_values[section] = {}

            for key in options:
                if config.has_section(section) and config.has_option(section, key):
                    original_values[section][key] = config.get(section, key)

        # Set new values
        for section, options in config_dict.items():
            for key, value in options.items():
                config.set(section, key, value)

        try:
            yield
        finally:
            # Restore original values
            for section, options in original_values.items():
                for key, value in options.items():
                    config.set(section, key, value)

    return _with_values
