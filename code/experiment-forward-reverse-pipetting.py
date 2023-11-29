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
from config.config import PATH_TO_NETWORK_DATA, PATH_TO_NETWORK_WELL_HX

def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(PATH_TO_NETWORK_WELL_HX, skipinitialspace=True)
    well_hx = well_hx.dropna(subset=['experiment id'])
    well_hx = well_hx.drop_duplicates(subset=['experiment id'])
    well_hx = well_hx[well_hx['experiment id'] != 'None']
    well_hx['experiment id'] = well_hx['experiment id'].astype(int)
    last_experiment_id = well_hx['experiment id'].max()
    return int(last_experiment_id+1)

# Create experiments
COLUMNS = 'ABCDEFGH'
ROWS = 12
PROJECT_ID = 7
EXPERIMENT_NAME = 'Forward Reverse Pipetting'
VOLUME = 100
PREVIOUS_CAMPAIGN_ID = 6

## We will be looping through 6 wellplates - changing the wellplate, and project campaign id
## Our volume will be the same for every well

for i in range(1,2):
    # Change wellplate and load new wellplate
    controller.load_new_wellplate(new_wellplate_type_number=6)
    experiment_id = determine_next_experiment_id()
    experiments = []

    # Create 96 new experiemnts for water
    for column in COLUMNS:
    #ex: for column in 'A':
        for row in range(1,ROWS+1):
        #ex: for row in range(1,13):
            experiments.append(experiment_class.ExperimentBase(
                    id=experiment_id,
                    experiment_name= EXPERIMENT_NAME,
                    priority= 1,
                    target_well= column + str(row),
                    pin = CURRENT_PIN,
                    project_id=PROJECT_ID,
                    project_campaign_id=PREVIOUS_CAMPAIGN_ID+i,
                    solutions={'water': VOLUME},
                    status='new',
                    filename='forward-reverse-pipetting_' + str(experiment_id),
                    )
                )
            experiment_id += 1

    scheduler = Scheduler()
    result = scheduler.add_nonfile_experiments(experiments)
    if result == 'success':
        controller.main(use_mock_instruments=True)
    else:
        print('Error: ', result)
controller.load_new_wellplate()
print('Finished running forward reverse pipetting experiments')
