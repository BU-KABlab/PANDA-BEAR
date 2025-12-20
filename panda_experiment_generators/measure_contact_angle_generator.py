"""Experiment parameters for the edot screening experiments"""

from pydantic import ValidationError

from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 300
EXPERIMENT_NAME = "measure_CA"
CAMPAIGN_ID = 5
PLATE_TYPE = 8


def main():
    """Runs the contact angle measurement experiment generator."""

    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    try:
        # num_experiments = 13
        well_id = {"A5"}
        for well in well_id:
            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_name="measure_contact_angle_protocol",
                    analysis_id=999,  # TODO: Update with actual analysis ID
                    well_id=well,
                    wellplate_type_id=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    solutions={
                        "acn": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "water": {"volume": 0, "concentration": 0.0, "repeated": 1},
                    },
                    rinse_sol_name="acn",
                    rinse_vol=200,
                    rinse_count=3,
                    flush_sol_name="acn",
                    flush_sol_vol=200,
                    flush_count=3,
                    filename=EXPERIMENT_NAME + "_" + str(experiment_id),
                    # Echem specific
                    ocp=0,
                    baseline=0,
                    cv=0,
                    ca=0,
                )
            )
            experiment_id += 1

        scheduler.schedule_experiments(experiments)

    except ValidationError as e:
        raise e
