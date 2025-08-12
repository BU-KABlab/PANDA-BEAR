"""Generator for the pipette tip replacement test protocol."""

import pandas as pd  # kept for parity with your other generator
from pydantic import ValidationError

from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 300
EXPERIMENT_NAME = "pipette_tip_test"
CAMPAIGN_ID = 2
PLATE_TYPE = 8  # not used by the protocol itself, but included for model parity

def main():
    """Schedules one or more pipette-tip test experiments."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    try:
        num_experiments = 1  # adjust if you want multiple sequential runs
        for _ in range(num_experiments):
            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_name="pipette_tip_test_protocol",
                    analysis_id=0,  # no analysis for this hardware/db smoke test
                    well_id="A1",   # placeholder; protocol won’t use it
                    wellplate_type_id=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    # Solutions block kept to satisfy the same model fields your PAMA generator uses
                    solutions={
                        "pama_200": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "electrolyte": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "ipa": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "dmf": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "acn": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "water": {"volume": 0, "concentration": 0.0, "repeated": 1},
                    },
                    # Rinse/flush/mix are no-ops here but included to match your usual schema
                    rinse_sol_name="dmf",
                    rinse_vol=0,
                    rinse_count=0,
                    flush_sol_name="dmf",
                    flush_sol_vol=0,
                    flush_count=0,
                    mix_count=0,
                    mix_volume=0,
                    filename=f"{EXPERIMENT_NAME}_{experiment_id}",
                    # Echem flags disabled; the protocol won’t call echem anyway
                    ocp=0,
                    baseline=0,
                    cv=0,
                    ca=0,
                    ca_sample_period=0.0,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=0.0,
                    ca_step_1_time=0.0,
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.0,
                )
            )
            experiment_id += 1

        scheduler.schedule_experiments(experiments)

    except ValidationError as e:
        raise e
