import logging
from pathlib import Path
from typing import Optional, Tuple

from shared_utilities.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)
from shared_utilities.log_tools import timing_wrapper

from ..errors import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    OCPFailure,
)
from ..experiments.experiment_types import (
    EchemExperimentBase,
    ExperimentStatus,
)

TESTING = read_testing_config()

if TESTING:
    from hardware.gamry_potentiostat.gamry_control_mock import (
        GamryPotentiostat as echem,
    )
    from hardware.gamry_potentiostat.gamry_control_mock import (
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )
else:
    import hardware.gamry_potentiostat.gamry_control as echem
    from hardware.gamry_potentiostat.gamry_control import (
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )

config = read_config()

# Constants
try:
    AIR_GAP = config.getfloat("DEFAULTS", "air_gap")
    DRIP_STOP = config.getfloat("DEFAULTS", "drip_stop_volume")
    if TESTING:
        PATH_TO_DATA = Path(config.get("TESTING", "data_dir"))
        PATH_TO_LOGS = Path(config.get("TESTING", "logging_dir"))
    else:
        PATH_TO_DATA = Path(config.get("PRODUCTION", "data_dir"))
        PATH_TO_LOGS = Path(config.get("PRODUCTION", "logging_dir"))
except ConfigParserError as e:
    logging.error("Failed to read config file. Error: %s", e)
    raise e

# Set up logging
logger = logging.getLogger("panda")
testing_logging = logging.getLogger("panda")


@timing_wrapper
def chrono_amp(
    ca_instructions: EchemExperimentBase,
    file_tag: Optional[str] = None,
    custom_parameters: Optional[chrono_parameters] = None,
) -> EchemExperimentBase:
    """Perform chronoamperometry measurement sequence.

    Parameters
    ----------
    ca_instructions : EchemExperimentBase
        Experiment parameters and configuration
    file_tag : str, optional
        Additional identifier for output files
    custom_parameters : chrono_parameters, optional
        Override default chronoamperometry parameters

    Returns
    -------
    EchemExperimentBase
        Updated experiment instructions with results

    Raises
    ------
    OCPFailure
        If open circuit potential measurement fails
    CAFailure
        If chronoamperometry measurement fails
    DepositionFailure
        If overall deposition process fails
    """
    try:
        if TESTING:
            pstat = echem()
        else:
            pstat = echem
        pstat.pstatconnect()

        # echem OCP
        logger.info("Beginning eChem OCP of well: %s", ca_instructions.well_id)
        ca_instructions.set_status_and_save(ExperimentStatus.OCPCHECK)

        base_filename = pstat.setfilename(
            ca_instructions.experiment_id,
            file_tag + "_OCP_CA" if file_tag else "OCP_CA",
            ca_instructions.project_id,
            ca_instructions.project_campaign_id,
            ca_instructions.well_id,
        )
        ca_results = ca_instructions.results
        pstat.OCP(
            potentiostat_ocp_parameters.OCPvi,
            potentiostat_ocp_parameters.OCPti,
            potentiostat_ocp_parameters.OCPrate,
        )  # OCP
        pstat.activecheck()
        ocp_dep_pass, ocp_char_final_voltage = pstat.check_vf_range(base_filename)
        ca_results.set_ocp_ca_file(
            base_filename, ocp_dep_pass, ocp_char_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            ca_instructions.well_id,
            ocp_dep_pass,
        )

        # echem CA - deposition
        if not ocp_dep_pass:
            ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
            raise OCPFailure("CA")

        try:
            ca_instructions.set_status_and_save(ExperimentStatus.EDEPOSITING)
            logger.info(
                "Beginning eChem deposition of well: %s", ca_instructions.well_id
            )
            deposition_data_file = pstat.setfilename(
                ca_instructions.experiment_id,
                file_tag + "_CA" if file_tag else "CA",
                ca_instructions.project_id,
                ca_instructions.project_campaign_id,
                ca_instructions.well_id,
            )

            # FEATURE have chrono return the max and min values for the deposition
            # and save them to the results
            if custom_parameters:  # if not none then use the custom parameters
                chrono_params = custom_parameters
            else:
                chrono_params = chrono_parameters(
                    CAvi=ca_instructions.ca_prestep_voltage,
                    CAti=ca_instructions.ca_prestep_time_delay,
                    CAv1=ca_instructions.ca_step_1_voltage,
                    CAt1=ca_instructions.ca_step_1_time,
                    CAv2=ca_instructions.ca_step_2_voltage,
                    CAt2=ca_instructions.ca_step_2_time,
                    CAsamplerate=ca_instructions.ca_sample_period,
                )  # CA
            pstat.chrono(chrono_params)
            pstat.activecheck()
            ca_results.set_ca_data_file(deposition_data_file, context=file_tag)
        except Exception as e:
            ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during deposition: %s", e)
            raise CAFailure(
                ca_instructions.experiment_id, ca_instructions.well_id
            ) from e

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

    finally:
        pstat.pstatdisconnect()

    return ca_instructions


@timing_wrapper
def cyclic_volt(
    cv_instructions: EchemExperimentBase,
    file_tag: str = None,
    overwrite_inital_voltage: bool = True,
    custom_parameters: cv_parameters = None,
) -> Tuple[EchemExperimentBase]:
    """
    Cyclicvoltamety in a well. This includes the OCP and CV steps.
    Will perform OCP and then set the initial voltage for the CV based on the final OCP voltage.
    To not change the instructions object, set overwrite_inital_voltage to False.
    No pipetting is performed in this step.
    Rinse the electrode after characterization.

    WARNING: Do not change the instructions initial voltage during a custom CV unless you are sure that the instructions
    are meant to be changed. The initial voltage should only be changed during regular CV step.

    Args:
        char_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files
        overwrite_inital_voltage (bool): Whether to overwrite the initial voltage with the final OCP voltage
        custom_parameters (potentiostat_cv_parameters): The custom CV parameters to be used

    Returns:
        char_instructions (Experiment): The updated experiment instructions
        char_results (ExperimentResult): The updated experiment results
    """
    try:
        # echem OCP
        if file_tag:
            logger.info(
                "Beginning %s OCP of well: %s", file_tag, cv_instructions.well_id
            )
        else:
            logger.info("Beginning OCP of well: %s", cv_instructions.well_id)
        if TESTING:
            pstat = echem()
        else:
            pstat = echem

        pstat.pstatconnect()
        cv_instructions.set_status_and_save(ExperimentStatus.OCPCHECK)
        ocp_char_file = pstat.setfilename(
            cv_instructions.experiment_id,
            file_tag + "_OCP_CV" if file_tag else "OCP_CV",
            cv_instructions.project_id,
            cv_instructions.project_campaign_id,
            cv_instructions.well_id,
        )

        try:
            pstat.OCP(
                OCPvi=potentiostat_ocp_parameters.OCPvi,
                OCPti=potentiostat_ocp_parameters.OCPti,
                OCPrate=potentiostat_ocp_parameters.OCPrate,
            )  # OCP
            pstat.activecheck()

        except Exception as e:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during OCP: %s", e)
            raise OCPFailure("CV") from e
        (
            ocp_char_pass,
            ocp_final_voltage,
        ) = pstat.check_vf_range(ocp_char_file)
        cv_instructions.results.set_ocp_cv_file(
            ocp_char_file, ocp_char_pass, ocp_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            cv_instructions.well_id,
            ocp_char_pass,
        )

        if not ocp_char_pass:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("OCP of well %s failed", cv_instructions.well_id)
            raise OCPFailure("CV")

        # echem CV - characterization
        if cv_instructions.baseline == 1:
            test_type = "CV_baseline"
            cv_instructions.set_status_and_save(ExperimentStatus.BASELINE)
        else:
            test_type = "CV"
            cv_instructions.set_status_and_save(ExperimentStatus.CHARACTERIZING)

        logger.info(
            "Beginning eChem %s of well: %s", test_type, cv_instructions.well_id
        )

        characterization_data_file = pstat.setfilename(
            cv_instructions.experiment_id,
            file_tag + "_CV" if file_tag else test_type,
            cv_instructions.project_id,
            cv_instructions.project_campaign_id,
            cv_instructions.well_id,
        )
        cv_instructions.results.set_cv_data_file(characterization_data_file, file_tag)
        # FEATURE have cyclic return the max and min values for the characterization
        # and save them to the results
        if overwrite_inital_voltage:
            cv_instructions.cv_initial_voltage = ocp_final_voltage

        if custom_parameters:  # if not none then use the custom parameters
            cv_params = custom_parameters
            cv_params.CVvi = ocp_final_voltage  # still need to set the initial voltage, not overwriting the original
        else:
            cv_params = cv_parameters(
                CVvi=cv_instructions.cv_initial_voltage,
                CVap1=cv_instructions.cv_first_anodic_peak,
                CVap2=cv_instructions.cv_second_anodic_peak,
                CVvf=cv_instructions.cv_final_voltage,
                CVsr1=cv_instructions.cv_scan_rate_cycle_1,
                CVsr2=cv_instructions.cv_scan_rate_cycle_2,
                CVsr3=cv_instructions.cv_scan_rate_cycle_3,
                CVcycle=cv_instructions.cv_cycle_count,
            )

        try:
            pstat.cyclic(cv_params)
            pstat.activecheck()

        except Exception as e:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during CV: %s", e)
            raise CVFailure(
                cv_instructions.experiment_id, cv_instructions.well_id
            ) from e

    except OCPFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", cv_instructions.well_id)
        raise e
    except CVFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CV of well %s failed", cv_instructions.well_id)
        raise e
    except Exception as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("An unknown exception occurred during CV: %s", e)
        raise CVFailure(cv_instructions.experiment_id, cv_instructions.well_id) from e
    finally:
        pstat.pstatdisconnect()

    return cv_instructions


if __name__ == "__main__":
    pass
