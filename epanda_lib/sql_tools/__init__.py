# sql_tools/__init__.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from epanda_lib.config.config import SQL_DB_PATH
# Set up the database engine
engine = create_engine(SQL_DB_PATH)

# Set up the session factory
Session = sessionmaker(bind=engine)

# Optionally, you can also import your models here
from .models import Base, Experiment, ExperimentParameters

# Create all tables in the database (if they don't already exist)
Base.metadata.create_all(engine)
