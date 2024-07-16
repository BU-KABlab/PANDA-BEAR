# db_setup.py
from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

config = ConfigParser()
config.read("panda_lib/config/panda_sdl_config.ini")
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
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
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
