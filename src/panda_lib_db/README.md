# PANDA-BEAR Database Setup Tool

A tool for setting up and managing local SQLite databases for PANDA-BEAR.

## Features

- Create a new SQLite database with the PANDA schema
- Initialize the database using SQLAlchemy models or a SQL dump file
- Command-line interface for easy setup

## Installation

This tool is included in the PANDA-BEAR package. Install it with:

```bash
pip install -e .
```

From the root of the PANDA-BEAR repository.

## Usage

### Command Line Interface

After installation, you can use the `panda-db-setup` command to create a new database:

```bash
# Create a database with default settings
panda-db-setup

# Use a custom database path
panda-db-setup --db-path ./my_custom_db.db

# Use a custom SQL dump file
panda-db-setup --sql-dump ./my_custom_dump.sql

# Force overwrite of existing database
panda-db-setup --force

# Create only the schema without importing data
panda-db-setup --schema-only
```

### Python API

You can also use the Python API to set up a database programmatically:

```python
from panda_lib_db.db_setup import setup_database

# Set up a database with default SQL dump
setup_database(db_path="./my_database.db")

# Set up a database with a custom SQL dump
setup_database(
    db_path="./my_database.db", 
    sql_dump="./my_custom_dump.sql"
)

# Force overwrite existing database
setup_database(
    db_path="./my_database.db", 
    drop_existing=True
)
```

## Default Configuration

By default, the tool will:
- Create a database file named `panda.db` in the PANDA-BEAR root directory
- Use the SQL dump file at `sql_scripts/panda_db_dump.sql` to initialize the database

## Database Schema

The database schema is based on the SQLAlchemy models defined in `panda_models`. 
These models are used to create the database tables and relationships.