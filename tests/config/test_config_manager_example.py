"""
Example test that demonstrates how to use the test_config_manager
"""

import os

from shared_utilities.config.test_config_manager import (
    ConfigTestHelper,
    temporary_config,
)

# Import AFTER the test environment is set up to ensure the right config is used
# from shared_utilities.config.config_tools import read_config


def test_config_with_context_manager():
    """Test using the context manager for temporary config"""
    test_config = """
    [PANDA]
    version = 2.0
    unit_id = 99
    unit_name = "TestUnit"
    
    [OPTIONS]
    testing = True
    use_slack = False
    
    [MILL]
    port = MOCK_PORT
    baudrate = 9600
    """

    # Outside the context manager, we should have the normal config
    # Note: This test might not work as expected if run in a pytest session
    # that already has a global test config fixture

    with temporary_config(test_config) as config_path:
        # Import inside the context to ensure the right config is used
        from shared_utilities.config.config_tools import read_config

        # Now read_config() should return our test config
        config = read_config()

        # Verify the test config values are used
        assert config["PANDA"]["unit_id"] == "99"
        assert config["PANDA"]["unit_name"] == '"TestUnit"'
        assert config["MILL"]["port"] == "MOCK_PORT"

        # Print debug info to verify
        print(f"Using config file: {config_path}")
        print(f"PANDA_TESTING_MODE: {os.environ.get('PANDA_TESTING_MODE')}")
        print(f"PANDA_SDL_CONFIG_PATH: {os.environ.get('PANDA_SDL_CONFIG_PATH')}")


def test_config_with_helper_class():
    """Test using the ConfigTestHelper directly"""

    # Store original environment
    original_env = {}
    for var in [
        "PANDA_SDL_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_TESTING_CONFIG_PATH",
    ]:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create test config
    test_config_dict = {
        "PANDA": {"version": "2.0", "unit_id": "99", "unit_name": "TestUnit2"},
        "MILL": {"port": "ANOTHER_MOCK_PORT", "baudrate": "115200"},
    }

    # Create temp config file
    temp_path = ConfigTestHelper.create_test_config(test_config_dict)

    try:
        # Set up environment
        ConfigTestHelper.setup_test_environment(temp_path)

        # Import after environment is set up
        from shared_utilities.config.config_tools import read_config

        # Read the config
        config = read_config()

        # Verify values
        assert config["PANDA"]["unit_id"] == "99"
        assert config["MILL"]["port"] == "ANOTHER_MOCK_PORT"

    finally:
        # Clean up
        ConfigTestHelper.cleanup_test_environment(temp_path, original_env)


if __name__ == "__main__":
    # Run tests directly (useful for debugging)
    test_config_with_context_manager()
    test_config_with_helper_class()
    print("All tests passed!")
