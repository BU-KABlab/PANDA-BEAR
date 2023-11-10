"""
Using a 96 well plate, generate experiments to test the water
Each column is a replicate and every row is a different volume

"""

import experiment_class
#import numpy as np
import matplotlib.pyplot as plt
from config.pin import CURRENT_PIN
from scheduler import Scheduler
import controller
import pandas as pd
from pathlib import Path
controller.load_new_wellplate()
well_hx = pd.read_csv(Path.cwd() / 'data' / 'well_history.csv', skipinitialspace=True)
                    #     names= ["plate id", "type number", "well id","experiment id", "project id", "status", "status date", "contents"],
                    #     dtype={"plate id":int, "type number":int, "well id":str,"experiment id":int, "project id":int, "status":str, "status date":str, "contents":str},
                    #     skipinitialspace=True
                    #    )
last_experiment_id = well_hx['experiment id'].max()
COLUMNS = 'ABCDEFGH'
ROWS = 12
experiment_id = int(last_experiment_id+1)
PROJECT_ID = 3
EXPERIMENT_NAME = 'Water test'
experiments = []
# Create a new experiment
for column in COLUMNS:
#for column in 'A':
    volume = 130
    for row in range(1,ROWS+1):
    #for row in range(1,13):
        experiments.append(experiment_class.ExperimentBase(
                id=experiment_id,
                experiment_name= EXPERIMENT_NAME,
                priority= 1,
                target_well= column + str(row),
                pin = CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=1,
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
    controller.main()
else:
    print('Error: ', result)

# Create a dataframe to store the results
#results = pd.DataFrame(columns=['experiment_id', 'volume', 'mass'])

# # Run the experiments
# for experiment in experiments:
#     #experiment.run()
#     results = results.append({'experiment_id': experiment.id,
#                               'volume': experiment.volume,
#                               'mass': experiment.mass},
#                              ignore_index=True)

# # Plot the results
# plt.figure()
# plt.plot(results['volume'], results['mass'], 'o')
# plt.xlabel('Volume (mL)')
# plt.ylabel('Mass (g)')
# plt.title('Mass of water in 96 well plate')
# plt.show()
# plt.savefig('water_test.png')
