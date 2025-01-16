# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass
from logging import Logger

from panda_lib.actions import (
    ExperimentStatus,
    Toolkit,
    Well,
    chrono_amp,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)
from panda_lib.actions_pgma import cyclic_volt_pgma_fc

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiment_class import EchemExperimentBase

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
            cyclic_volt_pgma_fc(
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


def _ca_steps(
    exp: EchemExperimentBase, toolkit: Toolkit, file_tag: str, well: Well, log: Logger
):
    # CA
    try:
        toolkit.mill.safe_move(
            coordinates=well.top_coordinates,
            tool="electrode",
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        try:
            chrono_amp(
                ca_instructions=exp,
                file_tag=file_tag,
            )
        except Exception as e:
            log.error("CA Deposition failed")
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
    PreCharacterization(experiment, toolkit)
    PolyDeposition(experiment, toolkit)
    PostCharacterization(experiment, toolkit)
    experiment.set_status_and_save(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("Experiment complete")


def PreCharacterization(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the precharacterization steps for the experiment.

    This is necessary since the wells have some variability in their properties. So we can normalize
    against the precharacterization data.

    """
    log = toolkit.global_logger
    log.info("Running precharacterization for: " + exp.experiment_name)

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
        file_tag="CV_precharacterization",
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
    # NOTE: ACN Rinse not present in PGMA Protocol
    # flush_pipette("acnrinse", toolkit)
    # rinse_well(
    #     instructions=exp,
    #     toolkit=toolkit,
    #     alt_sol_name="acnrinse",
    #     alt_vol=120,
    #     alt_count=4,
    # )

    image_well(toolkit, exp, "Post Precharacterization")
    log.info("Precharacterization complete")


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

    _ca_steps(
        exp=exp,
        toolkit=toolkit,
        file_tag="CA_Deposition",
        well=well,
        log=log,
    )

    clear_well(toolkit, well)
    # rinse_well(exp, toolkit)
    image_well(toolkit, exp, "Post Deposition")
    log.info("PolyDeposition complete")


def PostCharacterization(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the PostCharacterization steps for the experiment.

    """
    log = toolkit.global_logger
    log.info("Running PostCharacterization for: " + exp.experiment_name)
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

    # Tranfer the reagent to the well
    transfer(
        volume=reag.volume,
        src_vessel=reag.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # CV
    _cv_steps(
        exp=exp,
        toolkit=toolkit,
        file_tag="CV_postcharacterization",
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
    image_well(
        toolkit=toolkit,
        instructions=exp,
        step_description="Post PostCharacterization",
    )
    log.info("PostCharacterization complete")
