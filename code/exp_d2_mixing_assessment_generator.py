"""For testing the contamination from the pipette tip"""
import json
import experiment_class
from config.pin import CURRENT_PIN
from config.config import WELL_HX, TESTING
from scheduler import Scheduler
import wellplate
import pandas as pd

def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True, sep="&")
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id = well_hx["experiment id"].max()
    return int(last_experiment_id + 1)


TEST = TESTING
print("TEST MODE: ", TEST)
# Create experiments
PROJECT_ID = 15
EXPERIMENT_NAME = "Mixing assessment (exp D2)"
print(f"Experiment name: {EXPERIMENT_NAME}")
CAMPAIGN_ID = 1
PUMPING_RATE = 0.3

#controller.load_new_wellplate(new_wellplate_type_number=6)
wellplate.load_new_wellplate(False,108,3)
experiment_id = determine_next_experiment_id()
experiments : list[experiment_class.EchemExperimentBase]= []
WELL_NUMBER = 2


# Create 3 new experiments for the type 1 process
for i in range(3):
    experiments.append(
        experiment_class.EchemExperimentBase(
            id=experiment_id,
            well_id='F' + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME,
            priority=1,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'5mm_fecn6': 120, '10mm_fecn6': 120, 'electrolyte': 120, 'rinse0': 120},
            solutions_corrected={'5mm_fecn6': 0, '10mm_fecn6': 0, 'electrolyte': 0, 'rinse0': 0},
            pumping_rate=PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + ' ' + str(experiment_id),
            override_well_selection=0,
            # Echem specific
            ocp=1,
            baseline=0,
            cv=1,
            ca=0,
            cv_step_size=0.002,
            cv_second_anodic_peak=-0.2,
            cv_first_anodic_peak=0.58,
            cv_scan_rate_cycle_1=0.050,
            cv_scan_rate_cycle_2=0.050,
            cv_scan_rate_cycle_3=0.050,
            cv_cycle_count=3,
            cv_initial_voltage=0.0,
            cv_final_voltage=0.5,
            cv_sample_period=0.1

        )
    )
    experiment_id += 1
    WELL_NUMBER += 1

CAMPAIGN_ID += 1


for experiment in experiments:
    ## Print a recipt of the wellplate and its experiments noting the solution and volume
    print(f"Experiment id: {experiment.id}")
    print(f"Well id: {experiment.well_id}")
    print(f"Solutions: {json.dumps(experiment.solutions)}")
    print(f"Pumping rate: {PUMPING_RATE}")
    print(f"Project campaign id: {experiment.project_id}.{experiment.project_campaign_id}\n")


# Add experiments to the queue and run them
input("Press enter to add the experiments")
scheduler = Scheduler()
scheduler.add_nonfile_experiments(experiments)
