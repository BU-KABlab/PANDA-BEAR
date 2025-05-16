"""
Tests for the new ConfigInterface class
"""

import os
from configparser import ConfigParser
from unittest.mock import patch

import pytest

from shared_utilities.config.config_interface import (
    ConfigInterface,
    create_test_config,
    get_config,
    is_testing_mode,
    reset_config,
)


def test_config_interface_basic():
    """Test basic functionality of ConfigInterface"""
    # Create a test configuration
    config = ConfigInterface()

    # Configure with dictionary
    config.from_dict(
        {
            "PANDA": {"version": "2.0", "unit_id": "99", "unit_name": "TestUnit"},
            "MILL": {"port": "TEST_PORT", "baudrate": "9600"},
        }
    )

    # Test getters
    assert config.get("PANDA", "unit_id") == "99"
    assert config.get_int("PANDA", "unit_id") == 99
    assert config.get("MILL", "port") == "TEST_PORT"
    assert config.get("PANDA", "nonexistent", "default") == "default"

    # Test has methods
    assert config.has_section("PANDA")
    assert config.has_option("PANDA", "unit_id")
    assert not config.has_section("NONEXISTENT")
    assert not config.has_option("PANDA", "nonexistent")


def test_config_interface_from_dict():
    """Test loading configuration from dictionary"""
    config = ConfigInterface()

    test_config = {
        "PANDA": {"version": "2.0", "unit_id": "99"},
        "OPTIONS": {"testing": "True"},
    }

    config.from_dict(test_config)

    # Test values are set correctly
    assert config.get("PANDA", "unit_id") == "99"
    assert config.get_bool("OPTIONS", "testing") is True

    # Test to_dict returns the correct structure
    config_dict = config.to_dict()
    assert "PANDA" in config_dict
    assert config_dict["PANDA"]["unit_id"] == "99"


def test_create_test_config():
    """Test the create_test_config utility function"""
    # Test with dictionary
    config_dict = {"PANDA": {"unit_id": "555", "unit_name": "TestUnit"}}

    config = create_test_config(config_dict)
    assert config.get("PANDA", "unit_id") == "555"

    # Test with string
    config_str = """
    [PANDA]
    unit_id = 777
    unit_name = StringConfig
    
    [MILL]
    port = STRING_PORT
    """

    config = create_test_config(config_str)
    assert config.get("PANDA", "unit_id") == "777"
    assert config.get("MILL", "port") == "STRING_PORT"

    # Test with ConfigParser
    parser = ConfigParser()
    parser["PANDA"] = {"unit_id": "888"}

    config = create_test_config(parser)
    assert config.get("PANDA", "unit_id") == "888"


def test_get_config_singleton():
    """Test that get_config returns a singleton instance"""
    # Reset to ensure clean state
    reset_config()

    # Get the config instance
    config1 = get_config()
    config2 = get_config()

    # Should be the same instance
    assert config1 is config2

    # Reset again
    reset_config()
    config3 = get_config()

    # Should be a new instance
    assert config1 is not config3


@pytest.fixture
def mock_test_config():
    """Fixture to set up test configuration environment"""
    # Store original environment
    original_env = {}
    for var in [
        "PANDA_TESTING_MODE",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Set testing environment
    os.environ["PANDA_TESTING_MODE"] = "1"

    # Reset config to ensure clean state
    reset_config()

    yield

    # Restore original environment
    for var in [
        "PANDA_TESTING_MODE",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var in original_env:
            os.environ[var] = original_env[var]
        elif var in os.environ:
            del os.environ[var]

    # Reset config again
    reset_config()


def test_is_testing_mode(mock_test_config):
    """Test detection of testing mode"""
    assert is_testing_mode() is True

    # Change environment variable
    os.environ["PANDA_TESTING_MODE"] = "0"
    assert is_testing_mode() is False

    # Set pytest environment variable
    os.environ["PYTEST_CURRENT_TEST"] = "some_test"
    assert is_testing_mode() is True

    # Clean up
    del os.environ["PYTEST_CURRENT_TEST"]


def test_patched_config():
    """Test using pytest monkeypatch to replace config"""
    with patch(
        "shared_utilities.config.config_interface._config_instance"
    ) as mock_config:
        # Set up mock methods
        mock_config.get.return_value = "mocked_value"
        mock_config.get_int.return_value = 999

        # Get the config (should return our mocked instance)
        config = get_config()

        # Test the mocked values
        assert config.get("ANY", "KEY") == "mocked_value"
        assert config.get_int("ANY", "KEY") == 999
