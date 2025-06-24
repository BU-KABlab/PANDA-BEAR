import logging
import os
from logging import Logger
from pathlib import Path
from typing import Optional, Tuple

from panda_shared.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)

config = read_config()
TESTING = read_testing_config()
PSTAT = config.get("POTENTIOSTAT", "model", fallback="gamry")

from ..exceptions import (  # noqa: E402
    CAFailure,
    CVFailure,
    DepositionFailure,
    OCPError,
    OCPFailure,
)
from ..experiments.experiment_types import (  # noqa: E402
    EchemExperimentBase,
    ExperimentStatus,
)
from ..labware.wellplates import Well  # noqa: E402
from ..toolkit import Toolkit  # noqa: E402

if TESTING:
    if PSTAT == "gamry":
        from panda_lib.hardware.gamry_potentiostat.gamry_control_mock import (
            GamryPotentiostat as echem,
        )
        from panda_lib.hardware.gamry_potentiostat.gamry_control_mock import (
            chrono_parameters as gamry_chrono_parameters,
            cv_parameters as gamry_cv_parameters,
            potentiostat_ocp_parameters as gamry_potentiostat_ocp_parameters,
        )
    elif PSTAT == "emstat":
        import panda_lib.hardware.emstat_potentiostat.emstat_control_mock as echem
        from panda_lib.hardware.emstat_potentiostat.emstat_control_mock import (
            chrono_parameters as emstat_chrono_parameters,
            cv_parameters as emstat_cv_parameters,
            potentiostat_ocp_parameters as emstat_potentiostat_ocp_parameters,
        )

    else:
        raise ValueError(
            f"Unsupported potentiostat model: {PSTAT}. Supported models are 'gamry' and 'emstat'."
        )
else:
    if PSTAT == "gamry":
        if os.name != "nt":
            print(
                "Gamry potentiostat is not supported on non-Windows systems.\n Reverting to mock implementation."
            )
            from panda_lib.hardware.gamry_potentiostat.gamry_control_mock import (
                GamryPotentiostat as echem,
            )
            from panda_lib.hardware.gamry_potentiostat.gamry_control_mock import (
                chrono_parameters as gamry_chrono_parameters,
                cv_parameters as gamry_cv_parameters,
                potentiostat_ocp_parameters as gamry_potentiostat_ocp_parameters,
            )
        else:
            import panda_lib.hardware.gamry_potentiostat.gamry_control as echem
            from panda_lib.hardware.gamry_potentiostat.gamry_control import (
                chrono_parameters as gamry_chrono_parameters,
                cv_parameters as gamry_cv_parameters,
                potentiostat_ocp_parameters as gamry_potentiostat_ocp_parameters,
            )
    elif PSTAT == "emstat":
        import panda_lib.hardware.emstat_potentiostat.emstat_control as echem
        from panda_lib.hardware.emstat_potentiostat.emstat_control import (
            chrono_parameters as emstat_chrono_parameters,
            cv_parameters as emstat_cv_parameters,
            potentiostat_ocp_parameters as emstat_potentiostat_ocp_parameters,
        )


# Constants
try:
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


def open_circuit_potential(
    file_tag: str,
    exp: Optional[EchemExperimentBase] = None,
    testing: bool = False,
) -> Tuple[bool, float]:
    """Perform open circuit potential measurement sequence.

    Parameters
    ----------
    file_tag : str
        Additional identifier for output files
    exp : EchemExperimentBase
        Experiment parameters and configuration

    Returns
    -------
    float
        The final open circuit potential voltage
    """
    well = "test"
    experiment = "test"
    try:
        if TESTING or testing:
            pstat = echem()
        else:
            pstat = echem

        pstat.pstatconnect()
        if exp:
            exp.set_status_and_save(ExperimentStatus.OCPCHECK)
            base_filename = pstat.setfilename(
                exp.experiment_id,
                file_tag + "_OCP" if file_tag else "OCP",
                PATH_TO_DATA,
                exp.project_id,
                exp.project_campaign_id,
                exp.well_id,
            )
            well = exp.well
            experiment = exp.experiment_id
        else:
            base_filename = pstat.setfilename(
                "test",
                file_tag + "_OCP" if file_tag else "OCP",
                PATH_TO_DATA,
                "test",
                "test",
                "test",
            )

        # Fill in the correct parameters based on the potentiostat type
        if PSTAT == "gamry":
            params: gamry_potentiostat_ocp_parameters
            params = gamry_potentiostat_ocp_parameters
        elif PSTAT == "emstat":
            params: emstat_potentiostat_ocp_parameters
            params = emstat_potentiostat_ocp_parameters
        else:
            raise ValueError(
                f"Unsupported potentiostat model: {PSTAT}. Supported models are 'gamry' and 'emstat'."
            )
        

        pstat.OCP(
            params
        )  # OCP
        pstat.activecheck()
        ocp_pass, ocp_final_voltage = pstat.check_vf_range(base_filename)
        exp.results.set_ocp_file(base_filename, ocp_pass, ocp_final_voltage, file_tag)
        logger.info(
            "OCP of well %s passed: %s",
            well,
            ocp_pass,
        )
        if not ocp_pass:
            exp.set_status_and_save(ExperimentStatus.ERROR)
            raise OCPError("OCP")
    except OCPError as e:
        exp.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", well)
        raise e
    except Exception as e:
        exp.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during OCP: %s", e)
        raise OCPFailure(experiment, well) from e
    finally:
        pstat.pstatdisconnect()
    return ocp_pass, ocp_final_voltage


ocp = open_circuit_potential


def ocp_check(
    exp: EchemExperimentBase,
    well: Well,
    file_tag: str,
    toolkit: Toolkit,
    log: Logger,
) -> Tuple[bool, float]:
    """Perform open circuit potential measurement sequence. If short circuit is detected,
    the mill will be raised by 0.5mm and the OCP will be retried, repeating this process up to 3 times.

    If the OCP fails to pass, the experiment status will be set to ERROR and an OCPError will be raised.

    Parameters
    ----------
    exp : EchemExperimentBase
        Experiment parameters and configuration
    file_tag : str
        Additional identifier for output files

    Returns
    -------
    float
        The final open circuit potential voltage
    """
    adjustment = 0.0
    adjust_by = 0.5  # mm
    for i in range(3):
        toolkit.mill.safe_move(
            coordinates=well.top_coordinates,
            tool="electrode",
            second_z_cord=toolkit.wellplate.echem_height + adjustment,
            second_z_cord_feed=100,
        )

        passed, potential = ocp(
            file_tag=file_tag,
            exp=exp,
        )

        if not passed:
            if (
                abs(potential) < 0.001
            ):  # if the potential is less than 1mV, then the counter electrode maybe touching the working electrode
                adjustment += adjust_by
                log.error("OCP failed to read a potential")
                log.error("Attempting to raise mill and retry")
                continue
            elif (
                abs(potential) > 1.0
            ):  # likely out of solution, and something else is wrong
                log.error("OCP voltage above 1V, likely out of solution")
                log.error("Aborting CV")
                exp.set_status_and_save(ExperimentStatus.ERROR)
                raise OCPError("CV")
            else:
                # If the OCP did not pass but is also not around 0 or above 1 there is likely an issue with the electrode
                log.error("OCP failed to pass")
                log.error("Aborting CV")
                exp.set_status_and_save(ExperimentStatus.ERROR)
                raise OCPError("CV")
        else:
            break


def perform_chronoamperometry(
    experiment: EchemExperimentBase,
    file_tag: Optional[str] = None,
    custom_parameters: Optional[gamry_chrono_parameters | emstat_chrono_parameters] = None,
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
        logger.info("Beginning eChem OCP of well: %s", experiment.well_id)
        experiment.set_status_and_save(ExperimentStatus.OCPCHECK)

        base_filename = pstat.setfilename(
            experiment.experiment_id,
            file_tag + "_OCP_CA" if file_tag else "OCP_CA",
            PATH_TO_DATA,
            experiment.project_id,
            experiment.project_campaign_id,
            experiment.well_id,
        )
        ca_results = experiment.results
        # Fill in the correct parameters based on the potentiostat type
        if PSTAT == "gamry":
            params: gamry_potentiostat_ocp_parameters
            params = gamry_potentiostat_ocp_parameters
        elif PSTAT == "emstat":
            params: emstat_potentiostat_ocp_parameters
            params = emstat_potentiostat_ocp_parameters
        else:
            raise ValueError(
                f"Unsupported potentiostat model: {PSTAT}. Supported models are 'gamry' and 'emstat'."
            )
        

        pstat.OCP(
            params
        )  # OCP
        pstat.activecheck()
        ocp_dep_pass, ocp_char_final_voltage = pstat.check_vf_range(base_filename)
        ca_results.set_ocp_ca_file(
            base_filename, ocp_dep_pass, ocp_char_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            experiment.well_id,
            ocp_dep_pass,
        )

        # echem CA - deposition
        if not ocp_dep_pass:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            raise OCPError("CA")

        try:
            experiment.set_status_and_save(ExperimentStatus.EDEPOSITING)
            logger.info("Beginning eChem deposition of well: %s", experiment.well_id)
            deposition_data_file = pstat.setfilename(
                experiment.experiment_id,
                file_tag + "_CA" if file_tag else "CA",
                PATH_TO_DATA,
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.well_id,
            )

            # FEATURE have chrono return the max and min values for the deposition
            # and save them to the results
            if custom_parameters:  # if not none then use the custom parameters
                chrono_params = custom_parameters
            else:
                
                if PSTAT == "gamry":
                    chrono_params = gamry_chrono_parameters(
                        CAvi=experiment.ca_prestep_voltage,
                        CAti=experiment.ca_prestep_time_delay,
                        CAv1=experiment.ca_step_1_voltage,
                        CAt1=experiment.ca_step_1_time,
                        CAv2=experiment.ca_step_2_voltage,
                        CAt2=experiment.ca_step_2_time,
                        CAsamplerate=experiment.ca_sample_period,
                    )  # CA
                elif PSTAT == "emstat":
                    chrono_params = emstat_chrono_parameters(
                        Estep=experiment.ca_step_1_voltage,
                        dt=experiment.ca_sample_period,
                        ttot=experiment.ca_step_1_time,
                        E2=experiment.ca_step_2_voltage, # TODO: I dont think this is right, we need to see how the emstat expects CA
                    )
            pstat.chrono(chrono_params)
            pstat.activecheck()
            ca_results.set_ca_data_file(deposition_data_file, context=file_tag)
        except Exception as e:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during deposition: %s", e)
            raise CAFailure(experiment.experiment_id, experiment.well_id) from e

    except OCPError as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", experiment.well_id)
        raise e

    except CAFailure as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CA of well %s failed", experiment.well_id)
        raise e

    except Exception as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(experiment.experiment_id, experiment.well_id) from e

    finally:
        pstat.pstatdisconnect()

    return experiment


ca = perform_chronoamperometry


def pulsed_chronoamperometry(
    experiment: EchemExperimentBase,
    pulse_count: int,
    pause_time: float,
    file_tag: Optional[str] = None,
    custom_parameters: Optional[gamry_chrono_parameters | emstat_chrono_parameters] = None,
) -> EchemExperimentBase:
    """Perform pulsed chronoamperometry measurement sequence.

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
        logger.info("Beginning eChem OCP of well: %s", experiment.well_id)
        experiment.set_status_and_save(ExperimentStatus.OCPCHECK)

        base_filename = pstat.setfilename(
            experiment.experiment_id,
            file_tag + "_OCP_CA" if file_tag else "OCP_CA",
            PATH_TO_DATA,
            experiment.project_id,
            experiment.project_campaign_id,
            experiment.well_id,
        )
        ca_results = experiment.results
        # Fill in the correct parameters based on the potentiostat type
        if PSTAT == "gamry":
            params: gamry_potentiostat_ocp_parameters
            params = gamry_potentiostat_ocp_parameters
        elif PSTAT == "emstat":
            params: emstat_potentiostat_ocp_parameters
            params = emstat_potentiostat_ocp_parameters
        else:
            raise ValueError(
                f"Unsupported potentiostat model: {PSTAT}. Supported models are 'gamry' and 'emstat'."
            )
        pstat.OCP(params)  # OCP
        pstat.activecheck()
        ocp_dep_pass, ocp_char_final_voltage = pstat.check_vf_range(base_filename)
        ca_results.set_ocp_ca_file(
            base_filename, ocp_dep_pass, ocp_char_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            experiment.well_id,
            ocp_dep_pass,
        )

        # echem CA - deposition
        if not ocp_dep_pass:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            raise OCPError("CA")

        try:
            experiment.set_status_and_save(ExperimentStatus.EDEPOSITING)
            logger.info("Beginning eChem deposition of well: %s", experiment.well_id)
            deposition_data_file = pstat.setfilename(
                experiment.experiment_id,
                file_tag + "_CA" if file_tag else "CA",
                PATH_TO_DATA,
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.well_id,
            )

            # FEATURE have chrono return the max and min values for the deposition
            # and save them to the results
            if custom_parameters:  # if not none then use the custom parameters
                chrono_params = custom_parameters
            else:
                if PSTAT == "gamry":
                    chrono_params = gamry_chrono_parameters(
                        CAvi=experiment.ca_prestep_voltage,
                        CAti=experiment.ca_prestep_time_delay,
                        CAv1=experiment.ca_step_1_voltage,
                        CAt1=experiment.ca_step_1_time,
                        CAv2=experiment.ca_step_2_voltage,
                        CAt2=experiment.ca_step_2_time,
                        CAsamplerate=experiment.ca_sample_period,
                    )  # CA
                elif PSTAT == "emstat":
                    chrono_params = emstat_chrono_parameters(
                        Estep=experiment.ca_step_1_voltage,
                        dt=experiment.ca_sample_period,
                        ttot=experiment.ca_step_1_time,
                        E2=experiment.ca_step_2_voltage,  # TODO: I dont think this is right, we need to see how the emstat expects CA
                    )

            for pulse in pulse_count:
                # Perform the pulse
                pstat.chrono(chrono_params)
                pstat.activecheck()
                ca_results.set_ca_data_file(deposition_data_file, context=file_tag)

                # OCV
                ocp_params = params.copy()
                ocp_params.ttot = pause_time

                pstat.OCP(ocp_params)
                pstat.activecheck()
                ca_results.set_ocp_ca_file(base_filename, True, 0.0, file_tag)

        except Exception as e:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during deposition: %s", e)
            raise CAFailure(experiment.experiment_id, experiment.well_id) from e

    except OCPError as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", experiment.well_id)
        raise e

    except CAFailure as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CA of well %s failed", experiment.well_id)
        raise e

    except Exception as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(experiment.experiment_id, experiment.well_id) from e

    finally:
        pstat.pstatdisconnect()

    return experiment


def perform_cyclic_voltammetry(
    experiment: EchemExperimentBase,
    file_tag: str = None,
    overwrite_inital_voltage: bool = True,
    custom_parameters: gamry_cv_parameters | emstat_cv_parameters = None,
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
            logger.info("Beginning %s OCP of well: %s", file_tag, experiment.well_id)
        else:
            logger.info("Beginning OCP of well: %s", experiment.well_id)
        if TESTING:
            pstat = echem()
        else:
            pstat = echem

        pstat.pstatconnect()
        experiment.set_status_and_save(ExperimentStatus.OCPCHECK)
        ocp_char_file = pstat.setfilename(
            experiment.experiment_id,
            file_tag + "_OCP_CV" if file_tag else "OCP_CV",
            PATH_TO_DATA,
            experiment.project_id,
            experiment.project_campaign_id,
            experiment.well_id,
        )

        try:
            # Fill in the correct parameters based on the potentiostat type
            if PSTAT == "gamry":
                params: gamry_potentiostat_ocp_parameters
                params = gamry_potentiostat_ocp_parameters
            elif PSTAT == "emstat":
                params: emstat_potentiostat_ocp_parameters
                params = emstat_potentiostat_ocp_parameters
            else:
                raise ValueError(
                    f"Unsupported potentiostat model: {PSTAT}. Supported models are 'gamry' and 'emstat'."
                )
            pstat.OCP(
                params,
            )  # OCP
            pstat.activecheck()

        except Exception as e:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during OCP: %s", e)
            raise OCPError("CV") from e
        (
            ocp_char_pass,
            ocp_final_voltage,
        ) = pstat.check_vf_range(ocp_char_file)
        experiment.results.set_ocp_cv_file(
            ocp_char_file, ocp_char_pass, ocp_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            experiment.well_id,
            ocp_char_pass,
        )

        if not ocp_char_pass:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("OCP of well %s failed", experiment.well_id)
            raise OCPFailure(experiment.experiment_id, experiment.well_id)

        # echem CV - characterization
        if experiment.baseline == 1:
            test_type = "CV_baseline"
            experiment.set_status_and_save(ExperimentStatus.BASELINE)
        else:
            test_type = "CV"
            experiment.set_status_and_save(ExperimentStatus.CHARACTERIZING)

        logger.info("Beginning eChem %s of well: %s", test_type, experiment.well_id)

        characterization_data_file = pstat.setfilename(
            experiment.experiment_id,
            file_tag + "_CV" if file_tag else test_type,
            PATH_TO_DATA,
            experiment.project_id,
            experiment.project_campaign_id,
            experiment.well_id,
        )
        # FEATURE have cyclic return the max and min values for the characterization
        # and save them to the results
        if overwrite_inital_voltage:
            experiment.cv_initial_voltage = ocp_final_voltage

        if custom_parameters:  # if not none then use the custom parameters
            cv_params = custom_parameters
            cv_params.CVvi = ocp_final_voltage  # still need to set the initial voltage, not overwriting the original
        else:
            if PSTAT == "gamry":
                cv_params = gamry_cv_parameters(
                    CVvi=experiment.cv_initial_voltage,
                    CVap1=experiment.cv_first_anodic_peak,
                    CVap2=experiment.cv_second_anodic_peak,
                    CVvf=experiment.cv_final_voltage,
                    CVsr1=experiment.cv_scan_rate_cycle_1,
                    CVsr2=experiment.cv_scan_rate_cycle_2,
                    CVsr3=experiment.cv_scan_rate_cycle_3,
                    CVcycle=experiment.cv_cycle_count,
                )
            elif PSTAT == "emstat":
                # Emstat CV parameters are different, so we need to set them accordingly
                if experiment.cv_cycle_count == 1:
                    cv_params = emstat_cv_parameters(
                        Eini=experiment.cv_initial_voltage,
                        Ev1=experiment.cv_first_anodic_peak,
                        Ev2=experiment.cv_second_anodic_peak,
                        Efin=experiment.cv_final_voltage,
                        sr=experiment.cv_scan_rate_cycle_1,
                        dE=experiment.cv_step_size,
                        nSweeps=1,  # Emstat does not support multiple sweeps in the same way
                    )
                else:
                    # For multiple sweeps, we can set the second sweep parameters
                    cv_params = emstat_cv_parameters(
                        Eini=experiment.cv_initial_voltage,
                        Ev1=experiment.cv_first_anodic_peak,
                        Ev2=experiment.cv_second_anodic_peak,
                        Efin=experiment.cv_final_voltage,
                        sr=experiment.cv_scan_rate_cycle_1,
                        dE=experiment.cv_step_size,
                        nSweeps= experiment.cv_cycle_count,
                        E2=experiment.cv_second_sweep_voltage,
                        sens2=experiment.cv_second_sweep_sensitivity,
                    )

        try:
            pstat.cyclic(cv_params)
            pstat.activecheck()

        except Exception as e:
            experiment.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during CV: %s", e)
            raise CVFailure(experiment.experiment_id, experiment.well_id) from e

    except OCPFailure as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", experiment.well_id)
        raise e

    except OCPError as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        raise e
    except CVFailure as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CV of well %s failed", experiment.well_id)
        raise e
    except Exception as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("An unknown exception occurred during CV: %s", e)
        raise CVFailure(experiment.experiment_id, experiment.well_id) from e
    finally:
        try:
            experiment.results.set_cv_data_file(characterization_data_file, file_tag)

        except Exception as e:
            logger.error("Failed to set CV data file: %s", e)

        pstat.pstatdisconnect()

    return experiment


cv = perform_cyclic_voltammetry


def move_to_and_perform_cv(
    exp: EchemExperimentBase,
    toolkit: Toolkit,
    file_tag: str,
    well: Well,
    log: Logger = logger,
):
    # CV
    try:
        ocp_check(
            exp=exp,
            well=well,
            file_tag=file_tag,
            toolkit=toolkit,
            log=log,
        )

        perform_cyclic_voltammetry(
            experiment=exp,
            file_tag=file_tag,
        )

    except OCPFailure as e:
        log.error("OCP failed at %s", toolkit.wellplate.echem_height)
        log.error("Attempting to raise mill and retry")
        raise e

    except OCPError as e:
        log.error("OCP failed")
        log.error(e)
        exp.set_status_and_save(ExperimentStatus.ERROR)
        raise e

    except CVFailure as e:
        log.error("CV failed")
        log.error(e)
        exp.set_status_and_save(ExperimentStatus.ERROR)
        raise e

    except Exception as e:
        log.error("CV postcharacterization failed")
        log.error(e)
        exp.set_status_and_save(ExperimentStatus.ERROR)
        raise e

    finally:
        toolkit.mill.rinse_electrode(3)


def move_to_and_perform_ca(
    exp: EchemExperimentBase,
    toolkit: Toolkit,
    file_tag: str,
    well: Well,
    log: Logger = logger,
):
    # CA
    try:
        ocp_check(
            exp=exp,
            well=well,
            file_tag=file_tag,
            toolkit=toolkit,
            log=log,
        )

        try:
            perform_chronoamperometry(
                experiment=exp,
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


if __name__ == "__main__":
    pass
