"""
Tests for the configuration example module
"""

from unittest.mock import MagicMock

from src.shared_utilities.config.config_interface import ConfigInterface
from src.shared_utilities.examples.config_example import (
    MillController,
    get_mill_port,
    get_unit_id,
    is_testing_enabled,
)


# Method 1: Use the patch_global_config fixture from config_fixtures.py
def test_using_patched_global_config(patch_global_config):
    # The patch_global_config fixture replaces the global configuration
    # with a test configuration

    # Now the functions will use the test configuration
    assert get_unit_id() == 99
    assert get_mill_port() == "MOCK_PORT"
    assert is_testing_enabled() is True


# Method 2: Create a custom test configuration directly
def test_with_manual_patch():
    # Import the module to patch
    import src.shared_utilities.config.config_interface as config_module

    # Store original
    original_config = config_module._config_instance

    # Create test config
    test_config = ConfigInterface()
    test_config.from_dict(
        {
            "PANDA": {"unit_id": "555"},
            "MILL": {"port": "TEST_PORT"},
            "OPTIONS": {"testing": "True"},
        }
    )

    # Replace global config
    config_module._config_instance = test_config

    try:
        # Test with our custom configuration
        assert get_unit_id() == 555
        assert get_mill_port() == "TEST_PORT"
    finally:
        # Always restore original
        config_module._config_instance = original_config


# Method 3: Use dependency injection for classes
def test_mill_controller_with_di():
    # Create a mock configuration
    mock_config = MagicMock(spec=ConfigInterface)

    # Configure the mock
    mock_config.get.side_effect = lambda section, key, default=None: {
        ("MILL", "port"): "MOCK_PORT_123",
        ("MILL", "baudrate"): "115200",
        ("MILL", "timeout"): "5.5",
    }.get((section, key), default)

    mock_config.get_int.side_effect = lambda section, key, default=None: {
        ("MILL", "baudrate"): 115200
    }.get((section, key), default)

    mock_config.get_float.side_effect = lambda section, key, default=None: {
        ("MILL", "timeout"): 5.5
    }.get((section, key), default)

    # Create controller with the mock config
    controller = MillController(config=mock_config)

    # Test the controller
    assert controller.connect() is True

    # Verify the mock was used correctly
    mock_config.get.assert_any_call("MILL", "port")
    mock_config.get_int.assert_any_call("MILL", "baudrate", 9600)
    mock_config.get_float.assert_any_call("MILL", "timeout", 10.0)


# Method 4: Use with_config_values fixture from config_fixtures.py
def test_with_config_values(with_config_values):
    # Temporarily override configuration values for this test
    with with_config_values(
        {"PANDA": {"unit_id": "777"}, "MILL": {"port": "TEMP_PORT"}}
    ):
        # Inside this block, functions will use the temporary values
        assert get_unit_id() == 777
        assert get_mill_port() == "TEMP_PORT"

    # Outside the block, values are restored
    # (would need to know the original values to assert here)
