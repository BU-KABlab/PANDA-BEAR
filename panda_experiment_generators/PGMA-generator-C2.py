"""
Author: Harley Quinn
Date: 2024-09-04
Description: For generation of PGMA-phenol experiments with 10 mm diameter wells,
the second campaign of PGMA experiments.
"""

import pandas as pd
from pathlib import Path
from panda_lib import experiment_class
from panda_lib.config.config_tools import read_testing_config, read_config
from panda_lib.sql_tools.sql_system_state import get_current_pin
from panda_lib.scheduler import Scheduler, determine_next_experiment_id

config = read_config()
TESTING = read_testing_config()
PROJECT_ID = 18
EXPERIMENT_NAME = "PGMA-screening-C2"
CAMPAIGN_ID = 1
DEFAULT_PUMPING_RATE = config.getfloat("DEFAULTS", "pumping_rate")
GENERATORS_DIR = Path(config.get("GENERAL", "generators_dir"))

print("TEST MODE: ", TESTING)
input("Press enter to continue")

params_df = pd.read_csv(
   GENERATORS_DIR / "LHS-Parameters-C2.csv"
)  # Update path with location on PANDA computer


def main():
    """Runs the PGMA experiment generator."""
    starting_experiment_id = determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_class.PGMAExperiment] = []

    for _, row in params_df.iterrows():
        dep_v = row["Voltage"]  # dep_V is used for deposition voltage
        dep_t = row["Time"]  # dep_t is used for deposition time

        experiments.append(
            experiment_class.PGMAExperiment(
                experiment_id=experiment_id,
                protocol_id='PGMA-protocol-C2',  # figure this out
                well_id="A1",
                well_type_number=7,
                experiment_name=EXPERIMENT_NAME,
                pin=get_current_pin(),
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={
                    "PGMA-phenol": 320,
                    "DMF-TBAPrinse": 320,
                    "FC": 320,
                    "DMFrinse": 320,
                    "ACNrinse": 320,
                },
                solutions_corrected={
                    "PGMA-phenol": 0,
                    "DMF-TBAPrinse": 0,
                    "FC": 0,
                    "DMFrinse": 0,
                    "ACNrinse": 0,
                },
                pumping_rate=DEFAULT_PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + " " + str(experiment_id),
                # Echem specific
                ocp=1,
                baseline=0,
                cv=1,
                ca=1,
                ca_sample_period=0.1,
                ca_prestep_voltage=0.0,
                ca_prestep_time_delay=0.0,
                ca_step_1_voltage=dep_v,
                ca_step_1_time=dep_t,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
                cv_step_size=0.002,
                cv_first_anodic_peak=0.8,
                cv_second_anodic_peak=-0.3,
                cv_scan_rate_cycle_1=0.025,
                cv_scan_rate_cycle_2=0.025,
                cv_scan_rate_cycle_3=0.025,
                cv_cycle_count=3,
                cv_initial_voltage=0.0,
                cv_final_voltage=0.0,
                cv_sample_period=0.1,
            )
        )

        experiment_id += 1

    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)
