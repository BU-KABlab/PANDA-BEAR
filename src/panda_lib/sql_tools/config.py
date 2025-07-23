"""
SQL Tools Configuration

This module provides configuration options for the SQL tools package.
It consolidates database connection settings and other related configurations.
"""

import os
from typing import Dict

from panda_shared.config.config_tools import read_config

# Read configuration once at import time
config = read_config()


def get_database_url() -> str:
    """
    Get the database URL based on the current configuration.

    Returns:
        The database connection URL string
    """
    # Check for temporary database environment variable
    if os.environ.get("TEMP_DB") == "1":
        return "sqlite:///temp.db"

    # Check if we're in testing mode
    if config.getboolean("OPTIONS", "TESTING", fallback=False):
        db_type = config.get("TESTING", "testing_db_type", fallback="sqlite")
        db_address = config.get("TESTING", "testing_db_address", fallback="test.db")
        db_user = config.get("TESTING", "testing_db_user", fallback="")
        db_password = config.get("TESTING", "testing_db_password", fallback="")
    else:
        # Use the full production_db_url if present
        db_url = config.get("PRODUCTION", "production_db_url", fallback="")
        if db_url:
            return db_url.strip('"')
        # fallback to manual construction if needed
        db_type = config.get("PRODUCTION", "production_db_type", fallback="sqlite")
        db_address = config.get("PRODUCTION", "production_db_address", fallback="panda.db")
        db_user = config.get("PRODUCTION", "production_db_user", fallback="")
        db_password = config.get("PRODUCTION", "production_db_password", fallback="")

    # Build the database URL based on the database type
    if db_type == "sqlite":
        return f"sqlite:///{db_address}"
    elif db_type == "postgresql":
        return f"postgresql://{db_user}:{db_password}@{db_address}"
    elif db_type == "mysql":
        # fallback construction if production_db_url is not set
        return f"mysql+pymysql://{db_user}:{db_password}@{db_address}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def get_sql_config() -> Dict[str, str]:
    """
    Get all SQL-related configuration parameters.

    Returns:
        A dictionary of SQL configuration parameters
    """
    return {
        "database_url": get_database_url(),
        "echo": config.getboolean("DATABASE", "echo", fallback=False),
        "pool_size": config.getint("DATABASE", "pool_size", fallback=5),
        "max_overflow": config.getint("DATABASE", "max_overflow", fallback=10),
        "pool_timeout": config.getint("DATABASE", "pool_timeout", fallback=30),
    }
