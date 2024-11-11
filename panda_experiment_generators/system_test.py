"""Experiment parameters for the edot screening experiments"""

import pandas as pd

from panda_lib import experiment_class
from pydantic import ValidationError
from panda_lib import scheduler

PROJECT_ID = 999
EXPERIMENT_NAME = "system_test"
CAMPAIGN_ID = 999
PLATE_TYPE = 4

params_df = pd.read_csv(
    r".\panda_experiment_generators\system_test_params.csv"
)  # Update path with location on PANDA computer


def main():
    """Runs the edot voltage sweep experiment generator."""

    # controller.load_new_wellplate(new_wellplate_type_number=6)
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_class.PEDOTExperiment] = []

    try:
        for _, row in params_df.iterrows():
            dep_v = row["dep_V"]  # dep_V is used for deposition voltage
            dep_t = row["dep_T"]  # dep_T is used for deposition time

            experiments.append(
                experiment_class.PEDOTExperiment(
                    experiment_id=experiment_id,
                    protocol_id="system_test",
                    analysis_id=999,
                    well_id="A1",
                    well_type_number=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    solutions={
                        "edot": {"volume": 120, "concentration": 0.01, "repeated": 1},
                        "liclo4": {"volume": 120, "concentration": 1.0, "repeated": 1},
                        "rinse": {"volume": 120, "concentration": 1.0, "repeated": 4},
                    },
                    flush_sol_name="rinse",
                    flush_sol_vol=120,
                    flush_conc=3,
                    filename=EXPERIMENT_NAME + "_" + str(experiment_id),
                    # Echem specific
                    ocp=1,
                    baseline=0,
                    cv=0,
                    ca=1,
                    ca_sample_period=0.1,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=dep_v,
                    ca_step_1_time=dep_t,
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.5,
                )
            )
            experiment_id += 1

        scheduler.add_nonfile_experiments(experiments)

    except ValidationError as e:
        raise e
