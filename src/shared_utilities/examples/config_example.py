"""
Example module demonstrating usage of the new ConfigInterface

This module shows how to properly use the new configuration interface in your code.
"""

from shared_utilities.config.config_interface import get_config


def get_unit_id() -> int:
    """
    Get the unit ID from configuration

    Returns:
        Unit ID as integer
    """
    # Get the shared configuration object
    config = get_config()

    # Get the unit ID, with a default value of 99
    return config.get_int("PANDA", "unit_id", 99)


def get_mill_port() -> str:
    """
    Get the mill port from configuration

    Returns:
        Mill port as string
    """
    config = get_config()
    return config.get("MILL", "port", "COM1")


def is_testing_enabled() -> bool:
    """
    Check if testing mode is enabled

    Returns:
        True if testing is enabled, False otherwise
    """
    config = get_config()
    return config.get_bool("OPTIONS", "testing", False)


def get_db_connection_params() -> dict:
    """
    Get database connection parameters based on environment

    Returns:
        Dictionary with database connection parameters
    """
    config = get_config()

    # Determine which section to use based on testing mode
    if is_testing_enabled():
        section = "TESTING"
    else:
        section = "PRODUCTION"

    # Return connection params
    return {
        "db_type": config.get(section, "testing_db_type", "sqlite"),
        "db_address": config.get(section, "testing_db_address", "temp.db"),
        "db_user": config.get(section, "testing_db_user", None),
        "db_password": config.get(section, "testing_db_password", None),
    }


# Example of a class that uses configuration
class MillController:
    """Example class that uses configuration"""

    def __init__(self, config=None):
        """
        Initialize the mill controller

        Args:
            config: Configuration interface (optional, will use global config if None)
        """
        # Allow dependency injection of configuration for easier testing
        self.config = config or get_config()

    def connect(self):
        """Connect to the mill"""
        port = self.config.get("MILL", "port")
        baudrate = self.config.get_int("MILL", "baudrate", 9600)
        timeout = self.config.get_float("MILL", "timeout", 10.0)

        # In a real implementation, this would connect to the mill
        print(
            f"Connecting to mill on {port} with baudrate {baudrate} and timeout {timeout}"
        )

        return True
