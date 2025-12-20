"""Experiment parameters for the dmfc system check experiments"""

from pydantic import ValidationError
from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 300
EXPERIMENT_NAME = "dmfc_systemcheck"
CAMPAIGN_ID = 6
PLATE_TYPE = 8


def main():
    """Runs the dmfc system check experiment generator."""

    # controller.load_new_wellplate(new_wellplate_type_number=6)
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    try:
        # num_experiments = 13
        well_id = {"A4"}
        for well in well_id:
            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_name="dmfc_cv_protocol",
                    analysis_id=999,
                    well_id=well,
                    wellplate_type_id=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    solutions={
                        "dmfc": {"volume": 0, "concentration": 100, "repeated": 1},
                        "electrolyte": {
                            "volume": 0,
                            "concentration": 0.0,
                            "repeated": 1,
                        },
                        "ipa": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "dmf": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "acn": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "water": {"volume": 0, "concentration": 0.0, "repeated": 1},
                    },
                    rinse_sol_name="dmf",
                    rinse_vol=200,
                    rinse_count=3,
                    flush_sol_name="dmf",
                    flush_sol_vol=200,
                    flush_count=3,
                    dep_sol_conc=100,
                    filename=EXPERIMENT_NAME + "_" + str(experiment_id),
                    # Echem specific
                    ocp=1,
                    baseline=0,
                    cv=1,
                    ca=0,
                    cv_sample_period=0.1,
                    cv_initial_voltage=0.0,
                    cv_first_anodic_peak=1.0,
                    cv_second_anodic_peak=-0.4,
                    cv_final_voltage=0.0,
                    cv_step_size=0.01,
                    cv_cycle_count=3,
                    cv_scan_rate_cycle_1=0.1,
                )
            )
            experiment_id += 1

        scheduler.schedule_experiments(experiments)

    except ValidationError as e:
        raise e


3
