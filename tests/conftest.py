import os
import sys

import pytest

# Add the root directory of your project to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    from shared_utilities.config.config_tools import (
        read_config_value,
        write_config_value,
    )

    """Set up the config file for testing."""

    # Original Values
    testing = read_config_value("OPTIONS", "testing")
    testing_db_type = read_config_value("TESTING", "testing_db_type")
    testing_db_address = read_config_value("TESTING", "testing_db_address")
    testing_db_user = read_config_value("TESTING", "testing_db_user")
    testing_db_password = read_config_value("TESTING", "testing_db_password")

    write_config_value("OPTIONS", "testing", "True")
    write_config_value("OPTIONS", "memory_db", "True")
    write_config_value("TESTING", "testing_db_type", "sqlite")
    write_config_value("TESTING", "testing_db_address", ":memory:")
    write_config_value("TESTING", "testing_db_user", "None")
    write_config_value("TESTING", "testing_db_password", "None")
    yield
    write_config_value("OPTIONS", "testing", testing)
    write_config_value("OPTIONS", "memory_db", "False")
    write_config_value("TESTING", "testing_db_type", testing_db_type)
    write_config_value("TESTING", "testing_db_address", testing_db_address)
    write_config_value("TESTING", "testing_db_user", testing_db_user)
    write_config_value("TESTING", "testing_db_password", testing_db_password)
