"""
Author: Harley Quinn
Date: 2024-09-04
Description: For generation of PGMA-phenol experiments with 10 mm diameter wells,
the second campaign of PGMA experiments.
"""

from pathlib import Path

import pandas as pd

from panda_lib import scheduler
from panda_lib.experiments import experiment_types
from panda_lib.sql_tools.sql_system_state import get_current_pin
from shared_utilities.config.config_tools import read_config, read_testing_config

config = read_config()
TESTING = read_testing_config()
PROJECT_ID = 18
EXPERIMENT_NAME = "PGMA-screening-C2"
CAMPAIGN_ID = 1
PLATE_TYPE = 7  # 10 mm diameter wells
DEFAULT_PUMPING_RATE = config.getfloat("DEFAULTS", "pumping_rate")
GENERATORS_DIR = Path(config.get("GENERAL", "generators_dir"))
SYSTEM_VERSION = get_current_pin()

params_df = pd.read_csv(
    GENERATORS_DIR / "LHS-Parameters-C2.csv"
)  # Update path with location on PANDA computer


def main():
    """Runs the PGMA experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    for _, row in params_df.iterrows():
        dep_v = row["Voltage"]  # dep_V is used for deposition voltage
        dep_t = row["Time"]  # dep_t is used for deposition time

        experiments.append(
            experiment_types.EchemExperimentBase(
                experiment_id=experiment_id,
                protocol_id="PGMA-protocol-C2",  # figure this out
                well_id="A1",
                well_type_number=PLATE_TYPE,
                experiment_name=EXPERIMENT_NAME,
                pin=SYSTEM_VERSION,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={
                    "PGMA-phenol": 320,
                    "DMF-TBAPrinse": 320,
                    "FC": 320,
                    "DMFrinse": 320,
                    "ACNrinse": 320,
                },
                pumping_rate=DEFAULT_PUMPING_RATE,
                filename=str(experiment_id),
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

    scheduler.add_nonfile_experiments(experiments)
