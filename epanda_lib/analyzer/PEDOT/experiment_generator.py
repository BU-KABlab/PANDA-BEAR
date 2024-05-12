"""Generates a PEDOT experiment."""

from epanda_lib import experiment_class
from epanda_lib.config.config import DEFAULT_PUMPING_RATE
from epanda_lib.scheduler import Scheduler, determine_next_experiment_id
from epanda_lib.sql_utilities import get_current_pin

from .pedot_classes import PEDOTParams

CURRENT_PIN =  get_current_pin()

PROJECT_ID = 16


def pedot_generator(
    params: PEDOTParams, experiment_name="PEDOT_Optimization", campaign_id=0
) -> int:
    """Generates a PEDOT experiment."""
    experiment_id = determine_next_experiment_id()
    experiments: list[experiment_class.EdotExperiment] = []
    experiments.append(
        experiment_class.EdotExperiment(
            experiment_id=experiment_id,
            protocol_id=15,  # PEDOT protocol v4
            well_id="A1",  # Default to A1, let the program decide where else to put it
            well_type_number=4,
            experiment_name=experiment_name,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=campaign_id,
            solutions={"edot": 120, "liclo4": 0, "rinse": 120},
            solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
            pumping_rate=DEFAULT_PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
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
            ca_step_1_time=params.dep_t,
            ca_step_2_voltage=0.0,
            ca_step_2_time=0.0,
            ca_sample_rate=0.5,
            edot_concentration=params.concentration,
        )
    )

    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)
    return experiment_id
