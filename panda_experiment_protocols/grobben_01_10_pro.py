# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass

from panda_lib.actions.actions_default import (
    ExperimentStatus,
    Toolkit,
    Well,
    chrono_amp,
    clear_well,
    flush_pipette,
    image_well,
    mix,
    rinse_well,
    transfer,
)
from panda_lib.actions.actions_pgma import cyclic_volt_pgma_fc

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiments.experiment_types import EchemExperimentBase


@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int


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
        "pgma-pama-phenol",
        exp.solutions["pgma-pama-phenol"]["volume"],
        exp.solutions["pgma-pama-phenol"]["concentration"],
        1,
    )
    base = None
    for key in ["tea", "tpa", "teaa"]:
        if key in exp.solutions:
            base = Solution(
                key,
                exp.solutions[key]["volume"],
                exp.solutions[key]["concentration"],
                1,
            )
            break
    if base is None:
        log.error("No valid base found in the solutions.")
        return
    elyte = Solution(
        "tbap",
        exp.solutions["tbap"]["volume"],
        exp.solutions["tbap"]["concentration"],
        1,
    )
    well: Well = toolkit.wellplate.get_well(exp.well_id)
    exp.set_status_and_save(ExperimentStatus.IMAGING)
    log.info("Imaging the well")
    image_well(toolkit, exp, "New Well")
    exp.set_status_and_save(ExperimentStatus.PIPETTING)

    # Transfer the base to the well
    transfer(
        volume=base.volume,
        src_vessel=base.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Transfer the electrolyte to the well
    transfer(
        volume=elyte.volume,
        src_vessel=elyte.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Transfer the reagent to the well last to avoid sticking to the bottom
    transfer(
        volume=reag.volume,
        src_vessel=reag.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Mix the contents of the well
    mix(
        toolkit=toolkit,
        well=well,
        volume=well.volume,
        mix_count=3,
        mix_height=well.top,
    )

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
                file_tag="CV_precharacterization",
            )
        except Exception as e:
            log.error("CV precharacterization failed")
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

    clear_well(toolkit, well)
    flush_pipette(
        flush_with="dmf-tbaprinse",
        toolkit=toolkit,
    )
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="dmf-tbaprinse",
        alt_vol=120,
        alt_count=4,
    )

    image_well(toolkit, exp, "Post Precharacterization")
    log.info("Precharacterization complete")


def PolyDeposition(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the PolyDeposition steps for the experiment.

    """
    log = toolkit.global_logger
    log.info("Running PolyDeposition for: " + exp.experiment_name)
    reag = Solution(
        "pgma-pama-phenol",
        exp.solutions["pgma-pama-phenol"]["volume"],
        exp.solutions["pgma-pama-phenol"]["concentration"],
        1,
    )
    # The base we are using changes with each campaign but we follow the same protocol.
    # This step checks to see which base is present in the instructions and uses that.
    base = None
    for key in ["tea", "tpa", "teaa"]:
        if key in exp.solutions:
            base = Solution(
                key,
                exp.solutions[key]["volume"],
                exp.solutions[key]["concentration"],
                1,
            )
            break
    if base is None:
        log.error("No valid base found in the solutions.")
        return
    elyte = Solution(
        "tbap",
        exp.solutions["tbap"]["volume"],
        exp.solutions["tbap"]["concentration"],
        1,
    )
    well: Well = toolkit.wellplate.get_well(exp.well_id)
    exp.set_status_and_save(ExperimentStatus.IMAGING)
    log.info("Imaging the well")
    image_well(toolkit, exp, "New Well")
    exp.set_status_and_save(ExperimentStatus.PIPETTING)

    # Transfer the base to the well
    transfer(
        volume=base.volume,
        src_vessel=base.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Transfer the electrolyte to the well
    transfer(
        volume=elyte.volume,
        src_vessel=elyte.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Transfer the reagent to the well
    transfer(
        volume=reag.volume,
        src_vessel=reag.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Mix the contents of the well
    mix(
        toolkit=toolkit,
        well=well,
        volume=well.volume,
        mix_count=3,
        mix_height=well.top,
    )

    # CV
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
                file_tag="CA_Deposition",
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

    clear_well(toolkit, well)
    flush_pipette(
        flush_with="dmf-tbaprinse",
        toolkit=toolkit,
    )
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
    )
    image_well(
        toolkit=toolkit,
        instructions=exp,
        step_description="Post Deposition",
    )
    log.info("PolyDeposition complete")


def PostCharacterization(exp: EchemExperimentBase, toolkit: Toolkit):
    """
    Run the PostCharacterization steps for the experiment.

    """
    log = toolkit.global_logger
    log.info("Running PostCharacterization for: " + exp.experiment_name)
    reag = Solution(
        "pgma-pama-phenol",
        exp.solutions["pgma-pama-phenol"]["volume"],
        exp.solutions["pgma-pama-phenol"]["concentration"],
        1,
    )

    # The base we are using changes with each campaign but we follow the same protocol.
    # This step checks to see which base is present in the instructions and uses that.
    base = None
    for key in ["tea", "tpa", "teaa"]:
        if key in exp.solutions:
            base = Solution(
                key,
                exp.solutions[key]["volume"],
                exp.solutions[key]["concentration"],
                1,
            )
            break
    if base is None:
        log.error("No valid base found in the solutions.")
        return
    elyte = Solution(
        "tbap",
        exp.solutions["tbap"]["volume"],
        exp.solutions["tbap"]["concentration"],
        1,
    )
    well: Well = toolkit.wellplate.get_well(exp.well_id)
    exp.set_status_and_save(ExperimentStatus.IMAGING)
    log.info("Imaging the well")
    image_well(toolkit, exp, "New Well")
    exp.set_status_and_save(ExperimentStatus.PIPETTING)

    # Transfer the base to the well
    transfer(
        volume=base.volume,
        src_vessel=base.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Transfer the electrolyte to the well
    transfer(
        volume=elyte.volume,
        src_vessel=elyte.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # transfer the reagent to the well
    transfer(
        volume=reag.volume,
        src_vessel=reag.name,
        dst_vessel=well,
        toolkit=toolkit,
    )

    # Mix the contents of the well
    mix(
        toolkit=toolkit,
        well=well,
        volume=well.volume,
        mix_count=3,
        mix_height=well.top,
    )

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
                file_tag="CV_postcharacterization",
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
