"""For testing the contamination from the pipette tip"""
import json
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
PROJECT_ID = 13
EXPERIMENT_NAME = "Contamination assessment (exp B)"
print(f"Experiment name: {EXPERIMENT_NAME}")
CAMPAIGN_ID = 0

solutions = [
    "5mm_fecn3",
    "electrolyte",
    "electrolye_rinse",
]

PUMPING_RATE = 0.3

controller.load_new_wellplate(new_wellplate_type_number=6)
experiment_id = determine_next_experiment_id()
experiments : list[experiment_class.ExperimentBase]= []
WELL_NUMBER = 1
# Create 3 new experiments for the solution
for i in range(3):
    experiments.append(
        experiment_class.ExperimentBase(
            id=experiment_id,
            well_id='A' + WELL_NUMBER,
            experiment_name=EXPERIMENT_NAME,
            priority=1,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'5mm_fecn3': 120, 'electrolyte': 120, 'electrolye_rinse': 120},
            pumping_rate=PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + str(experiment_id),
        )
    )
    experiment_id += 1
    CAMPAIGN_ID += 1
    WELL_NUMBER += 1

for experiment in experiments:
    ## Print a recipt of the wellplate and its experiments noting the solution and volume
    print(f"Experiment id: {experiment.id}")
    print(f"Solutions: {json.dumps(experiment.solutions)}")
    print(f"Plate number: {CAMPAIGN_ID}")
    print(f"Pumping rate: {PUMPING_RATE}")
    print(f"Project campaign id: {experiment.project_id}.{experiment.project_campaign_id}\n")


# Add experiments to the queue and run them
scheduler = Scheduler()
result = scheduler.add_nonfile_experiments(experiments)
if result == "success":
    controller.main(use_mock_instruments=TEST)
else:
    print("Error: ", result)

controller.load_new_wellplate(new_wellplate_type_number=6)
message = f"Finished running {EXPERIMENT_NAME} experiments"
print(message)
bot = SlackBot(test=TEST)
bot.send_slack_message(message=message, channel_id="alert")