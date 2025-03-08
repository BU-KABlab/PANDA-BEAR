# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass

from panda_lib import Toolkit
from panda_lib.actions import (
    clear_well,
    flush_pipette,
    image_well,
    move_to_and_perform_ca,
    rinse_well,
    transfer,
)

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiments import EchemExperimentBase, ExperimentStatus

# To have specific types for the wells, import them from the labware module.
from panda_lib.labware.wellplates import Well

reag_name = "pgma-pama-phenol-teaa-tbap"


@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int


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

    # Transfer the reagent to the well
    transfer(reag.volume, reag.name, well, toolkit)

    move_to_and_perform_ca(
        exp=exp,
        toolkit=toolkit,
        file_tag="CA_Deposition",
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
    image_well(toolkit, exp, "Post Deposition")
    log.info("PolyDeposition complete")
    exp.set_status_and_save(ExperimentStatus.COMPLETE)
