"""
Database setup tool for PANDA-BEAR

This module provides functions for setting up a local SQLite database
using the PANDA-BEAR SQLAlchemy models.
"""

import os
import sqlite3
import sys

import sqlalchemy as sa

# Import models - assuming they're available in panda_lib.sql_tools
from panda_lib.sql_tools.models import Base


def return_sql_dump_file():
    """Return the path to the SQL dump file."""
    # Get project root - assumes this script is in panda_lib_db folder
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Default SQL dump path
    sql_dump_path = os.path.join(project_root, "panda_db_dump.sql")

    return sql_dump_path


def create_engine(db_path, echo=False):
    """Create a SQLAlchemy engine for the database.

    Args:
        db_path: Path to the SQLite database file
        echo: Whether to echo SQL commands

    Returns:
        The SQLAlchemy engine
    """
    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Create SQLAlchemy engine
    engine_url = f"sqlite:///{db_path}"
    engine = sa.create_engine(engine_url, echo=echo)

    return engine


def init_db_from_models(db_path, drop_all=False):
    """Initialize database using SQLAlchemy models.

    Args:
        db_path: Path to the SQLite database file
        drop_all: Whether to drop all tables before creation

    Returns:
        The SQLAlchemy engine
    """
    engine = create_engine(db_path)

    if drop_all:
        Base.metadata.drop_all(engine)

    # Create tables from models
    Base.metadata.create_all(engine)

    return engine


def execute_sql_script(db_path, sql_path):
    """Execute a SQL script on the database.

    Args:
        db_path: Path to the SQLite database file
        sql_path: Path to the SQL script file

    Returns:
        None
    """
    # Read SQL script
    with open(sql_path, "r") as f:
        sql_script = f.read()

    # Execute script with SQLite directly
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()


def setup_database(db_path, sql_dump=None, drop_existing=False):
    """Set up a new database using models and optionally a SQL dump.

    Args:
        db_path: Path to the SQLite database file
        sql_dump: Path to a SQL dump file for initializing data
        drop_existing: Whether to drop the existing database

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if database exists
        db_exists = os.path.exists(db_path)

        if db_exists and not drop_existing:
            print(f"Database {db_path} already exists. Use --force to replace it.")
            return False

        # Initialize database from models
        _ = init_db_from_models(db_path, drop_all=drop_existing)

        # Apply SQL dump if provided
        if sql_dump and os.path.exists(sql_dump):
            print(f"Applying SQL dump from {sql_dump}")
            execute_sql_script(db_path, sql_dump)

        print(f"Database initialized at {db_path}")
        return True

    except Exception as e:
        print(f"Error setting up database: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from panda_shared.config.config_tools import read_config

    config = read_config()
    db_type = config.get("PRODUCTION", "production_db_type")
    db_address = config.get("PRODUCTION", "production_db_address")
    db_user = config.get("PRODUCTION", "production_db_user", fallback=None)
    db_password = config.get("PRODUCTION", "production_db_password", fallback=None)
    db_url = config.get("PRODUCTION", "production_db_url", fallback=None)

    if db_type == "sqlite":
        DATABASE_URL = f"sqlite:///{db_address}"
    elif db_type == "mysql":
        if db_url:
            DATABASE_URL = db_url.strip('"')
        else:
            import re

            match = re.match(r"([^:/]+):(\d+)/(.*)", db_address)
            if match:
                host, port, dbname = match.groups()
                DATABASE_URL = (
                    f"mysql+pymysql://{db_user}:{db_password}@{host}:{port}/{dbname}"
                )
            else:
                raise ValueError(f"Malformed db_address: {db_address}")
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        engine.connect()
        print("Connection successful")
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
