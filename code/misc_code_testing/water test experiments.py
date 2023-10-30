"""
Using a 96 well plate, generate experiments to test the water
Each column is a replicate and every row is a different volume

"""

import experiment_class
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from config.pin import CURRENT_PIN

COLUMNS = 'ABCDEFGH'
ROWS = 12
experiment_id = 9991000
PROJECT_ID = 3
EXPERIMENT_NAME = 'Water test'
experiments = []
# Create a new experiment
for column in COLUMNS:
    for row in range(ROWS):
        experiments.append(experiment_class.ExperimentBase(
                id=experiment_id,
                experiment_name= EXPERIMENT_NAME,
                priority= 1,
                target_well= column + str(row),
                pin = CURRENT_PIN,
                project_id=PROJECT_ID,
                solutions={'water': 1},
                status='new',
                )
            )
        experiment_id += 1

# Create a dataframe to store the results
results = pd.DataFrame(columns=['experiment_id', 'volume', 'mass'])

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
