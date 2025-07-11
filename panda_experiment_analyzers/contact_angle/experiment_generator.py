"""Generates a PAMA experiment."""

from contact_angle.ml_model.contact_angle_ml_analyzer import (
    main as run_ml_model,
)
from contact_angle_analyzer import analyze

from panda_lib import scheduler
from panda_lib.experiments import ExperimentStatus, experiment_types
from panda_lib.sql_tools.queries.system import get_current_pin

from .contact_angle_classes import PAMAParams

CURRENT_PIN = get_current_pin()

PROJECT_ID = 16 # TODO: update based on PAMA project number


def pama_generator(
    params: PAMAParams, experiment_name="PAMA_ContactAngle", campaign_id=0
) -> int:
    """Generates a PAMA experiment."""
    experiment_id = scheduler.determine_next_experiment_id()
    experiment = experiment_types.EchemExperimentBase(
        experiment_id=experiment_id,
        protocol_name=15,  # TODO: update this based on protocol used
        well_id="A1",  # Default to A1, let the program decide where else to put it
        well_type_number=4, #TODO: update based on new well plate type
        experiment_name=experiment_name,
        pin=str(CURRENT_PIN),
        project_id=PROJECT_ID,
        project_campaign_id=campaign_id,
        solutions={"edot": 120, "solvent": 0, "rinse": 120}, # TODO: update volumes and solutions
        status=ExperimentStatus.NEW,
        filename=experiment_name + " " + str(experiment_id),
        # Echem specific
        ocp=1,
        baseline=0,
        cv=0,
        ca=1,
        ca_sample_period=0.1,
        ca_prestep_voltage=0.0,
        ca_prestep_time_delay=0.0,
        ca_step_1_voltage=params.dep_v,
        ca_step_1_time=600,
        ca_step_2_voltage=0.0,
        ca_step_2_time=0.0,
        ca_sample_rate=0.5,
        pama_concentration=params.concentration,
        analyzer=analyze,
        generator=run_ml_model,
    )

    scheduler.schedule_experiments(
        [
            experiment,
        ]
    )
    return experiment_id
