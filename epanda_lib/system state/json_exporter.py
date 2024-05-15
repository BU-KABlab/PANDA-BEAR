import pandas as pd

# Load the JSON file into a pandas DataFrame
df = pd.read_json('epanda_lib\system state\waste_status.json')

# Save the DataFrame to a CSV file
df.to_csv('epanda_lib\system state\waste_status.csv', index=False)