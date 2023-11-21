"""
Using a 96 well plate, generate experiments to test the water
Each column is a replicate and every row is a different volume

"""
import experiment_class
#import numpy as np
#import matplotlib.pyplot as plt
from config.pin import CURRENT_PIN
from scheduler import Scheduler
import controller
import pandas as pd
from pathlib import Path

# Shelve current wellplate (unless new) and load new wellplate and reset vials
controller.load_new_wellplate()
controller.reset_vials("stock")
controller.reset_vials("waste")

# Load well history to get last experiment id
well_hx = pd.read_csv(Path.cwd() / 'data' / 'well_history.csv', skipinitialspace=True)
well_hx = well_hx.dropna(subset=['experiment id'])
well_hx = well_hx.drop_duplicates(subset=['experiment id'])
well_hx = well_hx[well_hx['experiment id'] != 'None']
well_hx['experiment id'] = well_hx['experiment id'].astype(int)
last_experiment_id = well_hx['experiment id'].max()
experiment_id = int(last_experiment_id+1)

# Create experiments
COLUMNS = 'ABCDEFGH'
ROWS = 12
PROJECT_ID = 6
EXPERIMENT_NAME = 'Water test'
PROJECT_CAMPAIGN_ID = 1
experiments = []
# Create 96 new experiemnts for water
for column in COLUMNS:
#ex: for column in 'A':
    volume = 130
    for row in range(1,ROWS+1):
    #ex: for row in range(1,13):
        experiments.append(experiment_class.ExperimentBase(
                id=experiment_id,
                experiment_name= EXPERIMENT_NAME,
                priority= 1,
                target_well= column + str(row),
                pin = CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=PROJECT_CAMPAIGN_ID,
                solutions={'water': volume},
                status='new',
                filename='water_test_' + str(experiment_id),
                )
            )
        experiment_id += 1
        volume -= 10

scheduler = Scheduler()
result = scheduler.add_nonfile_experiments(experiments)
if result == 'success':
    controller.main(use_mock_instruments=True)
else:
    print('Error: ', result)
