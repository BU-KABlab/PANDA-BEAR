# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass
from logging import Logger

from panda_lib.actions.actions_default import (
    ExperimentStatus,
    Toolkit,
    Well,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)
from panda_lib.actions.actions_pgma import cyclic_volt_pgma_pama

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiments.experiment_types import EchemExperimentBase

# Description
# Short protocol to run a CV with PGMA-PAMA-Phenol-TEAA-TBAP in order to observe the behavior over a
# range of voltages to inform future experiments.

reag_name = "pgma-pama-phenol-teaa-tbap"


@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int


def _cv_steps(
    exp: EchemExperimentBase, toolkit: Toolkit, file_tag: str, well: Well, log: Logger
):
    # CV
    try:
        toolkit.mill.safe_move(
            coordinates=well.top_coordinates,
            tool="electrode",
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        try:
            cyclic_volt_pgma_pama(
                cv_instructions=exp,
                file_tag=file_tag,
            )
        except Exception as e:
            log.error("CV postcharacterization failed")
            log.error(e)
            exp.set_status_and_save(ExperimentStatus.ERROR)
            raise e
    except Exception as e:
        log.error("Failed to move the mill to the well")
        log.error(e)
        exp.set_status_and_save(ExperimentStatus.ERROR)
        raise e

    finally:
        toolkit.mill.rinse_electrode(3)


def run(experiment: EchemExperimentBase, toolkit: Toolkit):
    """Run the experiment."""

    toolkit.global_logger.info("Running experiment: " + experiment.experiment_name)
    InitialPrecharacterization(experiment, toolkit)
    experiment.set_status_and_save(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("Experiment complete")


def InitialPrecharacterization(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the Initialcharacterization steps for the experiment.

    This is necessary since the wells have some variability in their properties. So we can normalize
    against the precharacterization data.

    """
    log = toolkit.global_logger
    log.info("Running Initialcharacterization for: " + exp.experiment_name)

    reag = Solution(
        reag_name,
        exp.solutions[reag_name]["volume"],
        exp.solutions[reag_name]["concentration"],
        1,
    )

    well: Well = toolkit.wellplate.get_well(exp.well_id)
    exp.set_status_and_save(ExperimentStatus.IMAGING)
    log.info("Imaging the well")
    image_well(toolkit, exp, "New Well")
    exp.set_status_and_save(ExperimentStatus.PIPETTING)

    # Transfer the reagent to the well last to avoid sticking to the bottom
    transfer(reag.volume, reag.name, well, toolkit)

    _cv_steps(
        exp=exp,
        toolkit=toolkit,
        file_tag="CV_initialcharacterization",
        well=well,
        log=log,
    )

    clear_well(toolkit, well)
    flush_pipette("dmfrinse", toolkit)
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="dmfrinse",
        alt_vol=120,
        alt_count=4,
    )
    flush_pipette("acnrinse", toolkit)
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="acnrinse",
        alt_vol=120,
        alt_count=4,
    )

    image_well(toolkit, exp, "Post Initialcharacterization")
    log.info("Initialcharacterization complete")
