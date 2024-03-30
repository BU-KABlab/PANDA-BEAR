
from datetime import datetime
import sqlalchemy
from typing import List
from pathlib import Path
import json
import csv
import dataclasses
import time
from enum import Enum

from epanda_lib.wellplate import Well

class ePANDADBTables(Enum):
    EXPERIMENT_RESULTS = "experiment_results"
    EXPERIMENTS = "experiments"
    GENERATORS = "generators"
    PROJECTS = "projects"
    PROTOCOLS = "protocols"
    QUEUE = "queue"
    SYSTEM_STATUS = "system_status"
    SYSTEM_VERSIONS = "system_versions"
    USERS = "users"
    WELL_HISTORY = "well_hx"
    WELLPLATES = "wellplates"
    WELLS = "wells"
    WELL_TYPES = "well_types"


class SQLTools:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = sqlalchemy.create_engine(db_url)
        self.connection = self.engine.connect()

    def get_table_columns(self, table_name: str) -> List[str]:
        result = self.connection.execute(f"SELECT * FROM {table_name} LIMIT 1")
        return result.keys()

    def get_table_data(self, table_name: str) -> List[dict]:
        result = self.connection.execute(f"SELECT * FROM {table_name}")
        return [dict(row) for row in result]

    def get_table_data_as_csv(self, table_name: str, output_file: str):
        result = self.connection.execute(f"SELECT * FROM {table_name}")
        with open(output_file, "w") as f:
            writer = csv.writer(f)
            writer.writerow(result.keys())
            for row in result:
                writer.writerow(row)

    def get_table_data_as_json(self, table_name: str, output_file: str):
        result = self.connection.execute(f"SELECT * FROM {table_name}")
        with open(output_file, "w") as f:
            json.dump([dict(row) for row in result], f)

    

