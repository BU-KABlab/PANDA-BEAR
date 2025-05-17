"""
A diagnostic script to test the configuration management
"""

import os
import sys
import tempfile

# Add the project root to sys.path if needed
if os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set logging to DEBUG to see more details
import logging

logging.basicConfig(level=logging.DEBUG)


def test_config_load():
    """Test if we can load a custom configuration during tests"""

    # Import the configuration tools
    from panda_shared.config.config_tools import (
        get_config_path,
        is_testing_mode,
        read_config,
        reload_config,
    )

    # Check initial state
    print("\n=== INITIAL STATE ===")
    print(f"Testing mode: {is_testing_mode()}")
    print(f"Current config path: {get_config_path()}")
    original_config = read_config()
    print(f"Current unit_id: {original_config.get('PANDA', 'unit_id')}")
    print(
        f"Current unit_name: {original_config.get('PANDA', 'unit_name', fallback='not set')}"
    )
    print(
        f"Current MILL port: {original_config.get('MILL', 'port', fallback='not set')}"
    )

    # Create a temp config file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_diag_")
    os.close(temp_fd)

    # Write test configuration
    test_config = """
[PANDA]
version = 2.0
unit_id = 555
unit_name = "TestDiagnostic"

[MILL]
port = TEST_PORT_HERE
baudrate = 9600
"""

    with open(temp_path, "w") as f:
        f.write(test_config)

    # Set environment variables
    print("\n=== SETTING UP TEST ENVIRONMENT ===")
    old_env_vars = {}
    for var in [
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var in os.environ:
            old_env_vars[var] = os.environ[var]

    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path

    print(f"Set PANDA_TESTING_MODE to: {os.environ.get('PANDA_TESTING_MODE')}")
    print(
        f"Set PANDA_TESTING_CONFIG_PATH to: {os.environ.get('PANDA_TESTING_CONFIG_PATH')}"
    )
    print(f"Set PANDA_SDL_CONFIG_PATH to: {os.environ.get('PANDA_SDL_CONFIG_PATH')}")

    # Force reload configuration
    print("\n=== RELOADING CONFIG ===")
    reload_config()

    # Check test state
    print("\n=== TEST STATE ===")
    print(f"Testing mode: {is_testing_mode()}")
    print(f"Current config path: {get_config_path()}")
    test_config = read_config()
    print(f"Current unit_id: {test_config.get('PANDA', 'unit_id')}")
    print(
        f"Current unit_name: {test_config.get('PANDA', 'unit_name', fallback='not set')}"
    )
    print(f"Current MILL port: {test_config.get('MILL', 'port', fallback='not set')}")

    # Now try importing a fresh copy of read_config
    print("\n=== IMPORTING FRESH READ_CONFIG ===")
    import importlib

    import panda_shared.config.config_tools as ct

    importlib.reload(ct)
    from panda_shared.config.config_tools import (
        read_config as fresh_read_config,
    )

    fresh_config = fresh_read_config()
    print(f"Fresh config unit_id: {fresh_config.get('PANDA', 'unit_id')}")
    print(
        f"Fresh config unit_name: {fresh_config.get('PANDA', 'unit_name', fallback='not set')}"
    )
    print(
        f"Fresh config MILL port: {fresh_config.get('MILL', 'port', fallback='not set')}"
    )

    # Clean up
    try:
        os.unlink(temp_path)
    except OSError:
        pass

    # Restore environment
    for var, value in old_env_vars.items():
        os.environ[var] = value

    for var in [
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
        "PANDA_SDL_CONFIG_PATH",
    ]:
        if var not in old_env_vars and var in os.environ:
            del os.environ[var]

    print("\n=== DONE ===")


if __name__ == "__main__":
    test_config_load()
