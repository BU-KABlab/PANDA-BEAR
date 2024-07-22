"""
db_setup.py

This script sets up the database connection and tests the connection to the
database. It reads the database configuration from the panda_sdl_config.ini
file and creates a connection to the database using SQLAlchemy. The script
also tests the connection to the database by executing a simple query to
retrieve the list of tables in the database.

The script uses the ConfigParser module to read the configuration file and
determine whether it's in testing or production mode. Based on the mode, it
reads the database configuration parameters such as the database type,
address, user, and password. It constructs the DATABASE_URL based on the
database type and creates an engine using SQLAlchemy. The script also defines
a sessionmaker object called SessionLocal, which is used to create a session
with the database. The test_connection() function tests the connection to the
database by connecting to the engine and executing a query to retrieve the
list of tables in the database. If the connection is successful, it prints
the list of tables; otherwise, it prints an error message.

The script can be run as a standalone script to test the connection to the
database.
"""

from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from panda_lib.config.config_tools import read_config

config = read_config()
# Determine if it's testing or production
if config.getboolean("OPTIONS", "testing"):
    db_type = config.get("TESTING", "testing_db_type")
    db_address = config.get("TESTING", "testing_db_address")
    db_user = config.get("TESTING", "testing_db_user", fallback=None)
    db_password = config.get("TESTING", "testing_db_password", fallback=None)
else:
    db_type = config.get("PRODUCTION", "production_db_type")
    db_address = config.get("PRODUCTION", "production_db_address")
    db_user = config.get("PRODUCTION", "production_db_user", fallback=None)
    db_password = config.get("PRODUCTION", "production_db_password", fallback=None)

# Construct the DATABASE_URL based on db_type
if db_type == "sqlite":
    DATABASE_URL = f"sqlite:///{db_address}"
elif db_type == "mysql":
    DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_address}"
else:
    raise ValueError(f"Unsupported database type: {db_type}")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Test connection from config file


def test_connection():
    """Test the connection to the database."""
    try:
        engine.connect()
        print("Connection successful")

        # Get a list of tables
        print("Tables in the database:")
        with SessionLocal() as session:
            if db_type == "sqlite":
                result = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table';")
                )
            else:
                result = session.execute(text("SHOW TABLES;"))
            for row in result:
                print(row)
    except Exception as e:
        print(f"Connection failed: {e}")
        raise e


if __name__ == "__main__":
    print()
    test_connection()
