"""For testing the contamination from the pipette tip"""
import json
import experiment_class
from config.pin import CURRENT_PIN
from scheduler import Scheduler
from wellplate import determine_next_experiment_id


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
    "5mm_fecn6",
    "electrolyte",
    "electrolye_rinse",
]

PUMPING_RATE = 0.3

#controller.load_new_wellplate(new_wellplate_type_number=6)
experiment_id = determine_next_experiment_id()
experiments : list[experiment_class.EchemExperimentBase]= []
WELL_NUMBER = 10
# Create 3 new experiments for the solution
for i in range(3):
    experiments.append(
        experiment_class.EchemExperimentBase(
            id=experiment_id,
            well_id='D' + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME,
            priority=1,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'5mm_fecn6': 120, 'electrolyte': 120, 'rinse0': 120},
            solutions_corrected={'5mm_fecn6': 120, 'electrolyte': 120, 'rinse0': 120},
            pumping_rate=PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + ' ' + str(experiment_id),

            # Echem specific
            baseline = 0,
            cv = 1,
            ca=0,
            ocp=1,
            cv_scan_rate=0.050,
            CVstep=0.02,
            CVap2=-0.2,
            CVap1=0.58,
            CVsr1=0.050,
            CVsr2=0.050,


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
