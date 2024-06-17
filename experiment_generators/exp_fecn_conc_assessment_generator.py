"""
FeCn concentration assessment
Author: Harley Quinn
Date: 2024-05-28
Description:
    For testing the contamination from the pipette tip

Reviewer: Gregory Robben
Date: 2024-06-01
    
"""

from panda_lib import experiment_class
from panda_lib.config.config import read_testing_config, DEFAULT_PUMPING_RATE
from panda_lib.sql_tools.sql_system_state import get_current_pin
from panda_lib.scheduler import Scheduler, determine_next_experiment_id

PROJECT_ID = 17
EXPERIMENT_NAME = "fecn_conc_assessment"
CAMPAIGN_ID = 0

print("TEST MODE: ", read_testing_config())
input("Press enter to continue")

def main():
    """Runs the edot voltage sweep experiment generator."""
    starting_experiment_id = determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_class.EchemExperimentBase] = []

    experiments.append(
        experiment_class.EchemExperimentBase(
            experiment_id=experiment_id,
            protocol_id=16,
            well_id='F1',
            well_type_number=4,
            experiment_name=EXPERIMENT_NAME,
            pin=get_current_pin(),
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'5mm_fecn6': 120, '10mm_fecn6': 0, 'electrolyte': 0, 'rinse': 120},
            solutions_corrected={'5mm_fecn6': 0, '10mm_fecn6': 0, 'electrolyte': 0, 'rinse': 0},
            pumping_rate=DEFAULT_PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + ' ' + str(experiment_id),
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

    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)
