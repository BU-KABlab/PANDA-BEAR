from pathlib import Path

import sqlalchemy
from sqlalchemy import text
print(sqlalchemy.__version__)

db_path = Path(
    "C:\\Users\\grego\\SynologyDrive\\Documents\\GitHub\\panda_bear\\epanda_test.db"
)
DB_DIALECT = "sqlite"

engine = sqlalchemy.create_engine(f"{DB_DIALECT}:///{db_path}")

with engine.connect() as connection:
    result = connection.execute(text("SELECT experiment_id FROM experiments"))
    for row in result:
        print("experiment ID:", row.experiment_id)
