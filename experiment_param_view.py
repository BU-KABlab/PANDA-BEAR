import sqlite3
from pathlib import Path

# Connect to the SQLite database
conn = sqlite3.connect(Path("//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/epanda_dev.db"))
c = conn.cursor()

# Drop the view if it exists
c.execute("DROP VIEW IF EXISTS experiment_params")

# Get the distinct parameter types
c.execute("SELECT DISTINCT parameter_name FROM experiment_parameters")
parameter_types = c.fetchall()

# Construct the dynamic SQL
sql_parts = [f"MAX(CASE WHEN parameter_name = '{param[0]}' THEN parameter_value END) AS {param[0]}" for param in parameter_types]
sql = "CREATE VIEW experiment_params AS SELECT experiment_id, " + ', '.join(sql_parts) + " FROM experiment_parameters GROUP BY experiment_id;"

# Execute the dynamic SQL
c.execute(sql)

# Commit the changes and close the connection
conn.commit()
conn.close()