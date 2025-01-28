"""Custom functions for the PANDA_SDL library which are specific to a particular experiment type."""

from panda_lib.actions.actions_default import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    ExperimentStatus,
    OCPFailure,
    Tuple,
    chrono_amp,
    chrono_parameters,
    cv_parameters,
    cyclic_volt,
    logger,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase


def chrono_amp_edot_bleaching(
    ca_instructions: EchemExperimentBase,
    file_tag: str = "CA_bleaching",
) -> Tuple[EchemExperimentBase]:
    """
    Bleaching of an edot film already on ITO. This wraps the chrono_amp function.

    Args:
        dep_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files
    Returns:
        dep_instructions (Experiment): The updated experiment instructions
    """
    try:
        logger.info("Setting up eChem bleaching process...")

        bleaching_params = chrono_parameters(
            CAvi=0.0,
            CAti=0.0,
            CAv1=-0.6,
            CAt1=60.0,
            CAv2=0.0,
            CAt2=0.0,
            CAsamplerate=0.1,
        )

        ca_instructions = chrono_amp(
            ca_instructions=ca_instructions,
            file_tag=file_tag,
            custom_parameters=bleaching_params,
        )

    except OCPFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", ca_instructions.well_id)
        raise e

    except CAFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CA of well %s failed", ca_instructions.well_id)
        raise e

    except Exception as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(
            ca_instructions.experiment_id, ca_instructions.well_id
        ) from e

    return ca_instructions


def chrono_amp_edot_coloring(
    ca_instructions: EchemExperimentBase,
    file_tag: str = "CA_coloring",
) -> Tuple[EchemExperimentBase]:
    """
    Coloring of an edot film already on ITO. This wraps the chrono_amp function.

    Args:
        dep_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files
    Returns:
        dep_instructions (Experiment): The updated experiment instructions
    """
    try:
        # echem setup
        logger.info("Setting up eChem coloring process...")

        coloring_params = chrono_parameters(
            CAvi=0.0,
            CAti=0.0,
            CAv1=0.5,
            CAt1=60.0,
            CAv2=0.0,
            CAt2=0.0,
            CAsamplerate=0.1,
        )

        ca_instructions = chrono_amp(
            ca_instructions=ca_instructions,
            file_tag=file_tag,
            custom_parameters=coloring_params,
        )

    except OCPFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", ca_instructions.well_id)
        raise e

    except CAFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CA of well %s failed", ca_instructions.well_id)
        raise e

    except Exception as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(
            ca_instructions.experiment_id, ca_instructions.well_id
        ) from e

    return ca_instructions


def cyclic_volt_edot_characterizing(
    cv_instructions: EchemExperimentBase, file_tag: str = "CV_characterization"
) -> Tuple[EchemExperimentBase]:
    """
    Characterization of the solutions on the substrate using CV.
    No pipetting is performed in this step.
    Rinse the electrode after characterization.

    Args:
        char_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files

    Returns:
        char_instructions (Experiment): The updated experiment instructions
    """
    try:
        logger.info("Characterizing well: %s", cv_instructions.well_id)

        characterizing_cyclic_volt_params = cv_parameters(
            CVvi=0.0,
            CVap1=0.8,
            CVap2=-0.8,
            CVvf=-0.8,
            CVsr1=0.04,
            CVsr2=0.04,
            CVsr3=0.04,
            CVsamplerate=0.002 / 0.04,
            CVcycle=3,
        )

        cv_instructions = cyclic_volt(
            cv_instructions=cv_instructions,
            file_tag=file_tag,
            # Do not change the instructions initial voltage during custom CV
            # We only change this for the deposition step which is the only step that
            # The instruction parameters apply to.
            overwrite_inital_voltage=False,
            custom_parameters=characterizing_cyclic_volt_params,
        )

    except OCPFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", cv_instructions.well_id)
        raise e

    except CVFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CV %s of well %s failed", file_tag, cv_instructions.well_id)
        raise e

    except Exception as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("An unknown exception occurred during %s CV: %s", file_tag, e)
        raise CVFailure(cv_instructions.experiment_id, cv_instructions.well_id) from e

    return cv_instructions
