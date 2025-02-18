# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass
from logging import Logger

from panda_lib import Toolkit
from panda_lib.actions import (
    cyclic_volt,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiments import EchemExperimentBase, ExperimentStatus

# To have specific types for the wells, import them from the labware module.
from panda_lib.labware.wellplates import Well

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
            cyclic_volt(
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
    PolyDeposition(experiment, toolkit)
    toolkit.global_logger.info("Experiment complete")


def PolyDeposition(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the PolyDeposition steps for the experiment.

    """
    log = toolkit.global_logger
    log.info("Running PolyDeposition for: " + exp.experiment_name)

    campaign_id = exp.project_campaign_id
    possible_reagents = ["pgma-pama-phenol-teaa-tbap","pgma-pama-teaa-tbap"]
    reag_name = possible_reagents[campaign_id]

    reag = Solution(
        reag_name,
        exp.solutions[reag_name]["volume"],
        exp.solutions[reag_name]["concentration"],
        1,
    )
    well: Well = toolkit.wellplate.get_well(exp.well_id)
    exp.set_status_and_save(ExperimentStatus.IMAGING)
    log.info("Imaging the well")
    image_well(toolkit, exp, "Pre CV")
    exp.set_status_and_save(ExperimentStatus.PIPETTING)

    # Transfer the reagent to the well
    transfer(reag.volume, reag.name, well, toolkit)

    _cv_steps(
        exp=exp,
        toolkit=toolkit,
        file_tag="CV_scan",
        well=well,
        log=log,
    )

    clear_well(toolkit, well)
    flush_pipette(
        flush_with="DMFrinse",
        toolkit=toolkit,
    )
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="DMFrinse",
    )
    flush_pipette(
        flush_with="ACNrinse",
        toolkit=toolkit,
    )
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="ACNrinse",
        alt_vol=120,
        alt_count=4,
    )
    image_well(toolkit, exp, "Post CV")
    log.info("PolyDeposition complete")
    exp.set_status_and_save(ExperimentStatus.COMPLETE)
