import pandas as pd
from pathlib import Path
from config.config import PATH_TO_NETWORK_LOGS, PATH_TO_NETWORK_DATA
from matplotlib import pyplot as plt

# ## ANALYSIS
#ids = [9992200, 9992151, 9992152, 9992153, 9992154, 9992155, 9992156, 9992157, 9992158, 9992159, 9992160, 9992161, 9992162, 9992163, 9992164]
project_ids = ['6']
# Load well history
#well_hx = pd.read_csv(Path.cwd() / 'data' / 'well_history.csv', skipinitialspace=True)
well_hx = pd.read_csv(PATH_TO_NETWORK_DATA + "/well_history.csv", skipinitialspace=True)
# Filter well history to those ids in the ids list
well_hx = well_hx[well_hx['project id'].astype(str).isin(project_ids)]
if len(well_hx) == 0:
    print('No experiments found for project ids: ' + str(project_ids))
    exit()
# Filter well history to only those experiments that were completed
well_hx = well_hx[well_hx['status'] == 'complete']

# Get the logs and filter to only those experiments in our filtered well history dataframe
# The logs have a formatted output of "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s"
logs = pd.read_csv(PATH_TO_NETWORK_LOGS + "/ePANDA.log", skipinitialspace=True, sep='&', header=None, names=['date', 'name', 'level', 'module', 'function', 'line', 'custom1', 'custom2', 'custom3', 'message'])

# filter on module = e_panda
logs = logs[logs['module'] == 'pump_control']

# set custom1 to str, custom2 to int, and custom3 to str
logs['custom1'] = logs['custom1'].astype(str)
logs['custom2'] = logs['custom2'].astype(int)
logs['custom3'] = logs['custom3'].astype(str)
# rename custom1 to campaign id, custom2 to experiment ID, custom3 to well
logs = logs.rename(columns={'custom1': 'campaign id', 'custom2': 'experiment id', 'custom3': 'well'})
# filter on experiment ids in the well history dataframe
logs = logs[logs['experiment id'].isin(well_hx['experiment id'])]

# filter on message containing 'Data'
logs = logs[logs['message'].str.contains('Data')]

# split message into 6 columns called 'message', 'action', 'volume', 'density', 'preweight', 'postweight'
logs[['message', 'action', 'volume', 'density', 'preweight', 'postweight']] = logs['message'].str.split(',', expand=True)

# add a column called 'weight change' that is postweight - preweight
logs['weight change'] = logs['postweight'].astype(float) - logs['preweight'].astype(float)

# add a column that is percent error betwen the actual weight change and the expected weight change based on the volume * density
logs['percent error'] = (logs['weight change'] - (logs['volume'].astype(float) * logs['density'].astype(float))) / (logs['volume'].astype(float) * logs['density'].astype(float))

# scatter Plot the percent error for each experiment, grouped by experiment id
logs.plot.scatter(x='experiment id', y='percent error', c='DarkBlue')
plt.xlabel('Experiment ID')
plt.ylabel('Percent Error')
plt.title('Percent Error by Experiment ID')
plt.show()
