"""
Command-line interface for PANDA-BEAR database setup

This module provides a CLI for setting up and managing PANDA-BEAR databases.
"""

import argparse
import os
import sys
from pathlib import Path

from panda_lib_db.db_setup import setup_database


def get_default_paths():
    """Get default paths for database and SQL dump files."""
    # Get project root - assumes this script is in panda_lib_db folder
    project_root = Path(__file__).parent.parent.absolute()

    # Default paths
    default_db_path = os.path.join(project_root, "panda.db")
    default_sql_dump = os.path.join(project_root, "panda_db_dump.sql")

    return default_db_path, default_sql_dump


def parse_args():
    """Parse command-line arguments."""
    default_db_path, default_sql_dump = get_default_paths()

    parser = argparse.ArgumentParser(description="PANDA-BEAR Database Setup Tool")

    # Database path argument
    parser.add_argument(
        "--db-path",
        "-d",
        type=str,
        default=default_db_path,
        help=f"Path to the SQLite database file (default: {default_db_path})",
    )

    # SQL dump argument
    parser.add_argument(
        "--sql-dump",
        "-s",
        type=str,
        default=default_sql_dump,
        help=f"Path to the SQL dump file (default: {default_sql_dump})",
    )

    # Force override flag
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite if database already exists",
    )

    # Schema-only flag
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Create only the schema without importing data from SQL dump",
    )

    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()

    # Get full paths
    db_path = os.path.abspath(args.db_path)
    sql_dump = None if args.schema_only else os.path.abspath(args.sql_dump)

    # Validate SQL dump path
    if sql_dump and not os.path.exists(sql_dump):
        print(f"SQL dump file not found: {sql_dump}", file=sys.stderr)
        return 1

    # Set up the database
    success = setup_database(
        db_path=db_path, sql_dump=sql_dump, drop_existing=args.force
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
