"""
The script generates a series of wellplates for calibration testing. Each wellplate is associated 
with a specific solution. The differences between each wellplate are:

Solutions: The script tests five different solutions, 'water, '1000:1 H20:Glycerol', 
'100:1 H20:Glycerol', '10:1 H20:Glycerol', and '1:1 H20:Glycerol'. The solutions are 
tested in that order, so the first wellplate will be associated with 'water', the 
second with '1000:1 H20:Glycerol', etc.

Volumes:
Each solution should get a calibration curve with experiments pipetting volumes from 
20µL - 140µL spaced apart by 10µL:
20,
30
40
50
60
70
80
90
100
110
120
130
140
Each volume should be done 8x for each solution.
So it winds up being 1 well plate of 96 experiment per solution.

Pumping Rate: Following the viscocity testing on 12/08/2023, 
the pumping rate will be set to 0.640 for all solutions.

Project Campaign ID: The project campaign ID is incremented for each solution, and thus 
each wellplate. The first wellplate will have a project campaign ID of 1, the second wellplate 
will have a project campaign ID of 2, etc.


Created on Tuesday December 11 2023
Created by: Gregory Robben
Reviewed by:
Reviewed on:

"""

import experiment_class
from config.pin import CURRENT_PIN
from config.config import WELL_HX
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


TEST = True
print("TEST MODE: ", TEST)
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
PROJECT_ID = 10
EXPERIMENT_NAME = "Calibration tests"
PREVIOUS_CAMPAIGN_ID = 0

solutions = [
    "water",
    "1000:1 H20:Glycerol",
    "100:1 H20:Glycerol",
    "10:1 H20:Glycerol",
    "1:1 H20:Glycerol",
]

volumes = [
           30,30,30,30,30,30,30, 30,
           40,40,40,40,40,40, 40, 40,
           50,50,50,50,50,50, 50,50,
           60,60,60,60,60,60, 60,60,
           70,70,70,70,70,70, 70,70,
           80, 80,80,80,80,80,80,80,
           90, 90,90,90,90,90,90,90,
           100, 100,100,100,100,100,100,100,
           110, 110,110,110,110,110,110,110,
           120,120,120,120,120,120,120,120,
            130,130,130,130,130,130,130,130,
           140,140,140,140,140,140,140,140,
           ]
PUMPING_RATE = 0.640
# iterate over the solutions we are testing
for solution_number, solution in enumerate(solutions):
    # for each solution we want one wellplate of 6x of each volume
    # Change wellplate and load new wellplate
    controller.load_new_wellplate(new_wellplate_type_number=6)
    experiment_id = determine_next_experiment_id()
    experiments : list[experiment_class.ExperimentBase]= []
    WELL_NUMBER = 0
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
                    project_id=9,
                    project_campaign_id=solution_number + 1,
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
    print(f"Experiment name: {EXPERIMENT_NAME}")
    print(f"Solution: {solution}")
    print(f"Plate number: {PREVIOUS_CAMPAIGN_ID + solution_number}")
    print(f"Pumping rate: {PUMPING_RATE}")
    print(f"Project campaign id: {PROJECT_ID}.{solution_number}\n")


    # Add experiments to the queue and run them
    scheduler = Scheduler()
    result = scheduler.add_nonfile_experiments(experiments)
    if result == "success":
        controller.main(use_mock_instruments=TEST)
    else:
        print("Error: ", result)
        break

controller.load_new_wellplate(new_wellplate_type_number=6)
message = f"Finished running {EXPERIMENT_NAME} experiments"
print(message)
bot = SlackBot(test=TEST)
bot.send_slack_message(message=message, channel_id="alert")
