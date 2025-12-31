"""Generator for the solid handling test protocol."""

from pydantic import ValidationError

from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 400
EXPERIMENT_NAME = "solid_handling_test"
CAMPAIGN_ID = 1
PLATE_TYPE = 9
# add plate type to SQL, panda_wellplate_types
# then add your specific wellplate to panda_wellplates

# it then adds the wells to panda_well_hx


def main():
    """Schedules one or more solid handling experiments."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    try:
        num_experiments = 1  # adjust if you want multiple sequential runs
        for _ in range(num_experiments):
            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_name="solid_handling_protocol",
                    well_id="A1",  # placeholder; protocol won’t use it
                    wellplate_type_id=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    filename=f"{EXPERIMENT_NAME}_{experiment_id}",
                )
            )
            experiment_id += 1

        scheduler.schedule_experiments(experiments)

    except ValidationError as e:
        raise e
