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
import json
import pandas as pd
from config.pin import CURRENT_PIN
from config.config import WELL_HX, WELL_STATUS
from scheduler import Scheduler
import controller
import experiment_class
from slack_functions2 import SlackBot


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True)
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id_in_well_hx = well_hx["experiment id"].max()

    ## Check the currently loaded wellplate for the last experiment id
    ## Then compare the well_hx experiment id to the last experiment id and choose the max
    ## This is to account for the case where the well_hx is empty or missing the current wellplate

    # Load the JSON file
    with open(WELL_STATUS, mode = "r", encoding= 'utf8') as f:
        data = json.load(f)

    # Normalize the 'wells' array into a DataFrame
    df = pd.json_normalize(data["wells"])

    # Convert experiment_id to numeric, errors='coerce' will turn non-numeric values into NaN
    df["experiment_id"] = pd.to_numeric(df["experiment_id"], errors="coerce")

    # Find the maximum experiment_id
    max_experiment_id = df["experiment_id"].max()
    last_experiment_id = max(last_experiment_id_in_well_hx, max_experiment_id)
    return int(last_experiment_id + 1)


TEST = True
print("TEST MODE: ", TEST)
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
PROJECT_ID = 9
EXPERIMENT_NAME = "Viscocity test"
VOLUME = 100
PREVIOUS_CAMPAIGN_ID = 3

## We will be looping through 6 wellplates - changing the wellplate, and project campaign id
## Our volume will be the same for every well

solutions = [
    "water",
"2:1 h20:glycerol",
"4:5 h20:glycerol",
"2:5 h20:glycerol"
]
# solutions = ["1:1 H20:Glycerol"]
## starting with the slowest, going up to the fastest
# 0.064 mL/min
# 0.138 mL/min
# 0.297 mL/min
# 0.64 mL/min
pumping_rates = [0.064, 0.138, 0.297, 0.640]
# pumping_rates = [0.297, 0.640]
# iterate over the solutions we are testing
for solution_number, solution in enumerate(solutions):
    # for each solution we want two wellplates
    for plate_number_per_solution in range(1, 3):
        # Change wellplate and load new wellplate
        plate_number = controller.load_new_wellplate(new_wellplate_type_number=6)
        experiment_id = determine_next_experiment_id()
        experiments: list[experiment_class.ExperimentBase] = []

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
                        project_campaign_id=PREVIOUS_CAMPAIGN_ID + solution_number+1,
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
                        # pumping_rate=pumping_rates[
                        #     (plate_number_per_solution - 1) * 2 + (column in "EFGH")
                        # ],
                        # pumping_rate = pumping_rates[plate_number_per_solution-1],
                        status=experiment_class.ExperimentStatus.NEW,
                        filename=EXPERIMENT_NAME + str(experiment_id),
                    )
                )
                experiment_id += 1

        ## Make sure we have 96 experiments
        assert len(experiments) == 96

        ## Chech that the pumping rates are correct for the plate number
        ## If the plate number is 0 then the pumping rate should be:
        ## 0.064 for the first 48 experiments
        ## 0.138 for the remaining 48 experiments
        ## If the plate number is 1, then the pumping rate should be:
        ## 0.297 for the first 48 experiments
        ## 0.640 for the remaining 48 experiments

    if plate_number_per_solution == 1:
        expected_pumping_rates = [0.064, 0.138]
    else:
        expected_pumping_rates = [0.297, 0.640]

    pumping_rates_in_experiments = [
        experiment.pumping_rate for experiment in experiments
    ]
    pumping_rates_first_48 = pumping_rates_in_experiments[:48]
    pumping_rates_remaining = pumping_rates_in_experiments[48:]

    expected_pumping_rate_first_48 = expected_pumping_rates[0]
    expected_pumping_rate_remaining = expected_pumping_rates[1]

    assert all(
        rate == expected_pumping_rate_first_48 for rate in pumping_rates_first_48
    ), "Pumping rate should be 0.064 or 0.297 for the first 48 experiments"
    assert all(
        rate == expected_pumping_rate_remaining for rate in pumping_rates_remaining
    ), "Pumping rate should be 0.138 or 0.640 for the remaining 48 experiments"
    ## Print a recipt of the wellplate and its experiments noting the pumping rate and solution
    print(f"Experiment name: {EXPERIMENT_NAME}")
    print(f"Solution: {solution}")
    print(f"Plate number: {plate_number}")
    print(f"Solution plate number: {plate_number_per_solution}")
    print(f"Pumping rate of first 0-47: {min(pumping_rates_first_48)}")
    print(f"Pumping rate of remaining 48-95: {min(pumping_rates_remaining)}")
    print(f"Project campaign id: {experiments[0].project_id}.{experiments[0].project_campaign_id}\n")

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
