"""
The script generates a series of wellplates for volume correction testing.

Volumes:
Each volume will have a correction factor applied to it. The correction factor is 
determined by the following equation:
Correction factor = 

Created on January 5 2024
Created by: Gregory Robben
Reviewed by:
Reviewed on:

"""

import experiment_class
from config.pin import CURRENT_PIN
from config.config import WELL_HX, TESTING
from scheduler import Scheduler
import controller
import pandas as pd
from slack_functions2 import SlackBot


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True)
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id = well_hx["experiment id"].max()
    return int(last_experiment_id + 1)


TEST = TESTING
print("TEST MODE: ", TEST)
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
WELLPLATE_TYPE_NUMBER = 6
PROJECT_ID = 11
EXPERIMENT_NAME = "Correction factor tests"
PREVIOUS_CAMPAIGN_ID = 0
print(f"Experiment name: {EXPERIMENT_NAME}")

solutions = [
    "water",
    "2:1 h2o:glycerol",
    "4:5 h2o:glycerol",
    "2:5 h2o:glycerol"
]

volumes = [
            30,30,30,30,30,30,30,30,
            40,40,40,40,40,40,40,40,
            50,50,50,50,50,50,50,50,
            60,60,60,60,60,60,60,60,
            70,70,70,70,70,70,70,70,
            80,80,80,80,80,80,80,80,
            90,90,90,90,90,90,90,90,
            100,100,100,100,100,100,100,100,
            110,110,110,110,110,110,110,110,
            120,120,120,120,120,120,120,120,
            130,130,130,130,130,130,130,130,
            140,140,140,140,140,140,140,140,
           ]
PUMPING_RATE = 0.3
experiment_id = determine_next_experiment_id()
# iterate over the solutions we are testing
for solution_number, solution in enumerate(solutions):
    # for each solution we want one wellplate of 6x of each volume
    # Change wellplate and load new wellplate
    controller.load_new_wellplate(new_wellplate_type_number=WELLPLATE_TYPE_NUMBER)
    experiments : list[experiment_class.ExperimentBase]= []
    WELL_NUMBER = 0
    campaign_id = PREVIOUS_CAMPAIGN_ID + solution_number + (1 if PREVIOUS_CAMPAIGN_ID != 0 else 0)
    # Create 6 new experiments for the solution
    for column in COLUMNS:
        # ex: for column in 'A':
        for row in range(1, ROWS + 1):
            # ex: for row in range(1,13):
            experiments.append(
                experiment_class.ExperimentBase(
                    id=experiment_id,
                    experiment_name=EXPERIMENT_NAME,
                    priority=1,
                    target_well=column + str(row),
                    pin=CURRENT_PIN,
                    project_id=PROJECT_ID,
                    project_campaign_id=campaign_id,
                    solutions={str(solution).lower(): float(volumes[WELL_NUMBER])},
                    pumping_rate=PUMPING_RATE,
                    status=experiment_class.ExperimentStatus.NEW,
                    filename=EXPERIMENT_NAME + str(experiment_id),
                )
            )
            experiment_id += 1
            WELL_NUMBER += 1


    ## Make sure we have 96 experiments
    assert len(experiments) == 96

    experiment_solutions = [solution for solution in solutions]
    experiment_volumes = [volume for volume in volumes]
    ## Print a recipt of the wellplate and its experiments noting the solution and volume
    print(f"Solution: {solution}")
    print(f"Plate number: {PREVIOUS_CAMPAIGN_ID + solution_number}")
    print(f"Pumping rate: {PUMPING_RATE}")
    print(f"Project campaign id: {PROJECT_ID}.{campaign_id}")
    ids = pd.DataFrame([experiment.id for experiment in experiments], columns=["experiment id"])
    print(f"Experiment IDs: {ids['experiment id'].min()} - {ids['experiment id'].max()}")
    print()

    # Add experiments to the queue and run them
    scheduler = Scheduler()
    if scheduler.add_nonfile_experiments(experiments): #fails if not all experiments are added
        controller.main(use_mock_instruments=TEST)
    else:
        print("Error loading experiments")
        break

controller.load_new_wellplate(new_wellplate_type_number=6)
message = f"Finished running {EXPERIMENT_NAME} experiments"
bot = SlackBot(test=TEST)
bot.send_slack_message(message=message, channel_id="alert")
