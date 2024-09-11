"""
Author: Harley Quinn
Date: 2024-06-21
Description: For generation of PGMA-phenol experiments
"""

from typing import List
import pandas as pd
from panda_lib import experiment_class
from panda_lib.config.config_tools import read_testing_config, read_config
from panda_lib.scheduler import Scheduler, determine_next_experiment_id

PROJECT_ID = 18
EXPERIMENT_NAME = "PGMA_dep_v1"
CAMPAIGN_ID = 0
# wellplate 108

print("TEST MODE: ", read_testing_config())
input("Press enter to continue")

config = read_config()
DEFAULT_PUMPING_RATE = config["DEFAULTS", "pumping_rate"]

params_df = pd.read_csv(
    r".\experiment_generators\exp_PGMA_high_conc_generator.csv"
)  # Update path with location on PANDA computer


def main():
    """Runs the PGMA experiment generator."""
    starting_experiment_id = determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: List[experiment_class.PGMAExperiment] = []

    for _, row in params_df.iterrows():
        dep_v = row["dep_V"]  # dep_V is used for deposition voltage

        experiments.append(
            experiment_class.PGMAExperiment(
                experiment_id=experiment_id,
                protocol_id=17,  # figure this out
                well_id="E2",
                well_type_number=3,
                experiment_name=EXPERIMENT_NAME,
                pin=1,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={
                    "pgma": 120,
                    "dmftbap_rinse": 100,
                    "fc": 120,
                    "dmf_rinse": 100,
                    "acn_rinse": 100,
                },
                solutions_corrected={
                    "pgma": 0,
                    "dmftbap_rinse": 0,
                    "fc": 0,
                    "dmf_rinse": 0,
                    "acn_rinse": 0,
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
                ca_step_1_time=200,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
                cv_step_size=0.002,
                cv_first_anodic_peak=1.0,
                cv_second_anodic_peak=-0.4,
                cv_scan_rate_cycle_1=0.025,
                cv_scan_rate_cycle_2=0.025,
                cv_scan_rate_cycle_3=0.025,
                cv_cycle_count=3,
                cv_initial_voltage=0.0,
                cv_final_voltage=-0.4,
                cv_sample_period=0.1,
            )
        )
        experiment_id += 1

    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)


if __name__ == "__main__":
    main()
