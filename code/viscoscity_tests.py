"""
Using a 96 well plate, generate experiments to test the water
Each column is a replicate and every row is a different volume

"""

import experiment_class
#import numpy as np
#import matplotlib.pyplot as plt
from config.pin import CURRENT_PIN
from config.config import PATH_TO_NETWORK_WELL_HX
from scheduler import Scheduler
import controller
import pandas as pd
from slack_functions2 import SlackBot

def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(PATH_TO_NETWORK_WELL_HX, skipinitialspace=True)
    well_hx = well_hx.dropna(subset=['experiment id'])
    well_hx = well_hx.drop_duplicates(subset=['experiment id'])
    well_hx = well_hx[well_hx['experiment id'] != 'None']
    well_hx['experiment id'] = well_hx['experiment id'].astype(int)
    last_experiment_id = well_hx['experiment id'].max()
    return int(last_experiment_id+1)

TEST = True
print('TEST MODE: ', TEST)
# Create experiments
COLUMNS = 'ABCDEFGH'
ROWS = 12
PROJECT_ID = 9
EXPERIMENT_NAME = 'Viscocity test'
VOLUME = 100
PREVIOUS_CAMPAIGN_ID = 31

## We will be looping through 6 wellplates - changing the wellplate, and project campaign id
## Our volume will be the same for every well
solutions = ['1000:1 H20:Glycerol', '100:1 H20:Glycerol', '10:1 H20:Glycerol', '1:1 H20:Glycerol']
pumping_rates = [0.064, 0.138, 0.297, 0.640]

# iterate over the solutions we are testing
for i, solution in enumerate(solutions):
    # for each solution we want two wellplates
    for j in range (1,3):
        # Change wellplate and load new wellplate
        controller.load_new_wellplate(new_wellplate_type_number=6)
        experiment_id = determine_next_experiment_id()
        experiments = []

        # Create 96 new experiemnts for the solution
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
                        solutions={str(solution): float(VOLUME)},
                        # for columns ABCD of the first wellplate use pumping rate 0.064,
                        # for columns EFGH of the first wellplate use pumping rate 0.138,
                        # for columns ABCD of the second wellplate use pumping rate 0.297,
                        # for columns EFGH of the second wellplate use pumping rate 0.640
                        pumping_rate = pumping_rates[i] if j == 1 else pumping_rates[i+2],
                        status='new',
                        filename=EXPERIMENT_NAME + str(experiment_id),
                        )
                    )
                experiment_id += 1

        scheduler = Scheduler()
        result = scheduler.add_nonfile_experiments(experiments)
        if result == 'success':
            controller.main(use_mock_instruments=TEST)
        else:
            print('Error: ', result)
            break

message = f'Finished running {EXPERIMENT_NAME} experiments'
print(message)
bot = SlackBot(test = TEST)
bot.send_slack_message(message=message, channel_id="alert")
