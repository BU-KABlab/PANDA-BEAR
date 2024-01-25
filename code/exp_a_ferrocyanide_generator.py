"""
For generating the ferrocyanide repeatability experiments.

The only involves one solution, FeCN6, however to test the conductivity of
the well plate we will be repeating the experiment in a triagle pattern
on the wellplate.

The apex of the two flat sides will be at h1, with the other corners at a1 and h12.
Each well is it own test.

The wellplate will look like this (x = test, o = no test):
    h g f e d c b a
1   x x x x x x x x
2   x o o o o o o x
3   x o o o o o x o
4   x o o o o x o o
5   x o o o o x o o
6   x o o o x o o o
7   x o o o x o o o
8   x o o x o o o o
9   x o o x o o o o
10  x o x o o o o o
11  x o x o o o o o
12  x x o o o o o o  
"""

from json import load
import time

import experiment_class
import pandas as pd
from config.config import TESTING, WELL_HX
from config.pin import CURRENT_PIN
from scheduler import Scheduler
from wellplate import load_new_wellplate

def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True,sep='&')
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
PROJECT_ID = 13
EXPERIMENT_NAME = "Repeatability assessment (exp A)"
print(f"Experiment name: {EXPERIMENT_NAME}")
CAMPAIGN_ID = 0

PUMPING_RATE = 0.3

# controller.load_new_wellplate(new_wellplate_type_number=6)
# controller.load_new_wellplate()
load_new_wellplate(False,108,3)
experiment_id = determine_next_experiment_id()
experiments: list[experiment_class.EchemExperimentBase] = []
WELL_NUMBER = 1

experiment_wells = [
    'H1',   'G1',   'F1',   'E1',   'D1',   'C1',   'B1',   'A1',
    'H2',                                                   'A2',
    'H3',                                           'B3',
    'H4',                                   'C4',
    'H5',                                   'C5',
    'H6',                           'D6',
    'H7',                           'D7',
    'H8',                   'E8',
    'H9',                   'E9',
    'H10',          'F10',
    'H11',          'F11',
    'H12', 'G12',
]

for col in COLUMNS:
    for row in range(1, ROWS + 1):
        if col + str(row) in experiment_wells:
            time.sleep(0.25)
            experiment = experiment_class.EchemExperimentBase(
                id=experiment_id,
                well_id=col + str(row),
                experiment_name=EXPERIMENT_NAME,
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"5mm_fecn6": 120, "electrolyte": 0, "rinse0": 0},
                solutions_corrected={"5mm_fecn6": 120, "electrolyte": 0, "rinse0": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + "_" + str(experiment_id),
                plate_id=108,
                # Echem specific
                ocp=1,
                baseline=0,
                cv=1,
                ca=0,
                cv_step_size=0.02,
                cv_second_anodic_peak=-0.2,
                cv_first_anodic_peak=0.58,
                cv_scan_rate_cycle_1=0.050,
                cv_scan_rate_cycle_2=0.050,
                cv_scan_rate_cycle_3=0.050,
            )

            experiments.append(experiment)
            experiment_id += 1

# Schedule experiments
scheduler = Scheduler()
scheduler.add_nonfile_experiments(experiments)
# for experiment in experiments:
#     ## Print a recipt of the wellplate and its experiments noting the solution and volume
#     print(experiment.print_experiment_parameters())
    
