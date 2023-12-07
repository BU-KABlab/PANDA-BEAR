"""
The script generates a series of wellplates for viscosity testing. Each wellplate is associated 
with a specific solution and pumping rate. The differences between each wellplate are:

Solution: The script tests four different solutions, each a different ratio of H20 to Glycerol. 
The solutions are '1000:1 H20:Glycerol', '100:1 H20:Glycerol', '10:1 H20:Glycerol', and 
'1:1 H20:Glycerol'. Each solution is tested on two wellplates.

Pumping Rate: For each solution, two different pumping rates are used. The pumping rates are 0.064, 
0.138, 0.297, and 0.640. For the first wellplate of each solution, the pumping rate is either 0.064 
or 0.138, depending on the column (ABCD uses 0.064, EFGH uses 0.138). For the second wellplate of 
each solution, the pumping rate is either 0.297 or 0.640, again depending on the column.

Project Campaign ID: The project campaign ID is incremented for each solution, so each wellplate 
associated with a different solution will have a different project campaign ID.


Created on Tuesday December 5 2023
Created by: Gregory Robben
Reviewed by:
Reviewed on:

"""

import experiment_class

# import numpy as np
# import matplotlib.pyplot as plt
from config.pin import CURRENT_PIN
from config.config import PATH_TO_NETWORK_WELL_HX
from scheduler import Scheduler
import controller
import pandas as pd
from slack_functions2 import SlackBot


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(PATH_TO_NETWORK_WELL_HX, skipinitialspace=True)
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id = well_hx["experiment id"].max()
    return int(last_experiment_id + 1)


TEST = False
print("TEST MODE: ", TEST)
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
PROJECT_ID = 9
EXPERIMENT_NAME = "Viscocity test"
VOLUME = 100
PREVIOUS_CAMPAIGN_ID = 0

## We will be looping through 6 wellplates - changing the wellplate, and project campaign id
## Our volume will be the same for every well
solutions = [
    "1000:1 H20:Glycerol",
    "100:1 H20:Glycerol",
    "10:1 H20:Glycerol",
    "1:1 H20:Glycerol",
]
pumping_rates = [0.064, 0.138, 0.297, 0.640]
# iterate over the solutions we are testing
for solution_number, solution in enumerate(solutions):
    # for each solution we want two wellplates
    for plate_number_per_solution in range(1, 3):
        # Change wellplate and load new wellplate
        controller.load_new_wellplate(new_wellplate_type_number=6)
        experiment_id = determine_next_experiment_id()
        experiments : list[experiment_class.ExperimentBase]= []

        # Create 96 new experiemnts for the solution
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
                        project_campaign_id=PREVIOUS_CAMPAIGN_ID + solution_number,
                        solutions={str(solution).lower(): float(VOLUME)},
                        # for columns ABCD of the plate 1 use pumping rate 0.064 (0),
                        # ex. plate_number_per_solution = 1, column = 'A' -> pumping rate = 0.064
                        # for columns EFGH of the plate 1 use pumping rate 0.138 (1),
                        # ex. plate_number_per_solution = 1, column = 'E' -> pumping rate = 0.138
                        # for columns ABCD of the plate 2 use pumping rate 0.297 (2),
                        # ex. plate_number_per_solution = 2, column = 'A' -> pumping rate = 0.297
                        # for columns EFGH of the plate 2 use pumping rate 0.640 (3)
                        # ex. plate_number_per_solution = 2, column = 'E' -> pumping rate = 0.640
                        pumping_rate = pumping_rates[
                            (plate_number_per_solution - 1) * 2
                            + (column in "EFGH")
                        ],

                        status = experiment_class.ExperimentStatus.NEW,
                        filename=EXPERIMENT_NAME + str(experiment_id),
                    )
                )
                experiment_id += 1

        ## Make sure we have 96 experiments
        assert len(experiments) == 96

        ## Chech that the pumping rates are correct for the plate number
        ## If the plate number is 0 then the pumping rate should be 0.064 for the first 48 experiments
        # and 0.138 for the remaining 48 experiments
        ## If the plate number is 1, then the pumping rate should be 0.297 for the first 48 experiments
        # and 0.640 for the remaining 48 experiments

        if plate_number_per_solution == 1:
            expected_pumping_rates = [0.064, 0.138]
        else:
            expected_pumping_rates = [0.297, 0.640]

        pumping_rates_in_experiments = [experiment.pumping_rate for experiment in experiments]
        pumping_rates_first_48 = pumping_rates_in_experiments[:48]
        pumping_rates_remaining = pumping_rates_in_experiments[48:]

        expected_pumping_rate_first_48 = expected_pumping_rates[0]
        expected_pumping_rate_remaining = expected_pumping_rates[1]

        assert all(rate == expected_pumping_rate_first_48 for rate in pumping_rates_first_48), "Pumping rate should be 0.064  or 0.297 for the first 48 experiments"
        assert all(rate == expected_pumping_rate_remaining for rate in pumping_rates_remaining), "Pumping rate should be 0.138 or 0.640 for the remaining 48 experiments"
        ## Print a recipt of the wellplate and its experiments noting the pumping rate and solution
        print(f"Solution: {solution}")
        print(f"Plate number: {PREVIOUS_CAMPAIGN_ID + solution_number}")
        print(f"Pumping rate of first 0-47: {expected_pumping_rate_first_48}")
        print(f"Pumping rate of remaining 48-95: {expected_pumping_rate_remaining}")
        print(f"Project campaign id: {PREVIOUS_CAMPAIGN_ID + solution_number}")

        scheduler = Scheduler()
        result = scheduler.add_nonfile_experiments(experiments)
        if result == "success":
            controller.main(use_mock_instruments=TEST)
        else:
            print("Error: ", result)
            break

message = f"Finished running {EXPERIMENT_NAME} experiments"
print(message)
bot = SlackBot(test=TEST)
bot.send_slack_message(message=message, channel_id="alert")
