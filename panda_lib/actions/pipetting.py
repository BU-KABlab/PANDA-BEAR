import logging
import math
from pathlib import Path
from typing import Optional, Union

from hardware.grbl_cnc_mill import Instruments
from hardware.panda_pipette.syringepump import MockPump, SyringePump
from shared_utilities.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)
from shared_utilities.log_tools import timing_wrapper

from ..experiments.experiment_types import (
    EchemExperimentBase,
    ExperimentBase,
    ExperimentStatus,
)
from ..labware import StockVial, Vial, WasteVial, Well
from ..panda_gantry import MockPandaMill as MockMill
from ..panda_gantry import PandaMill as Mill
from ..toolkit import Hardware, Labware, Toolkit
from ..utilities import Coordinates, correction_factor
from .movement import capping_sequence, decapping_sequence
from .vessel_handling import _handle_source_vessels, waste_selector

TESTING = read_testing_config()
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


def _pipette_action(
    toolkit: Union[Toolkit, Hardware],
    src_vessel: Union[Vial, Well],
    dst_vessel: Union[Well, WasteVial],
    desired_volume: float,
) -> None:
    """Perform pipetting action from source to destination vessel.

    Parameters
    ----------
    toolkit : Union[Toolkit, Hardware]
        The toolkit object containing mill and pump controls
    src_vessel : Union[Vial, Well]
        The source vessel to withdraw from
    dst_vessel : Union[Well, WasteVial]
        The destination vessel to deposit into
    desired_volume : float
        The volume to be transferred in microliters

    Notes
    -----
    This function handles the physical movement of liquid between vessels, including:
    - Air gap management
    - Decapping/capping of vials
    - Multi-step transfers for volumes exceeding pipette capacity
    """
    repetitions = math.ceil(
        desired_volume / (toolkit.pump.pipette.capacity_ul - DRIP_STOP)
    )
    if isinstance(src_vessel, Well):
        repetition_vol = correction_factor(desired_volume / repetitions, 1.0)
    else:
        repetition_vol = correction_factor(
            desired_volume / repetitions, src_vessel.viscosity_cp
        )
    logger.info(
        "Pipetting %f uL from %s to %s",
        desired_volume,
        src_vessel.name,
        dst_vessel.name,
    )

    for j in range(repetitions):
        logger.info("Repetition %d of %d", j + 1, repetitions)

        if isinstance(src_vessel, StockVial):
            decapping_sequence(
                toolkit.mill,
                Coordinates(src_vessel.x, src_vessel.y, src_vessel.top),
                toolkit.arduino,
            )

        toolkit.pump.withdraw(volume_to_withdraw=AIR_GAP)
        toolkit.mill.safe_move(
            src_vessel.x,
            src_vessel.y,
            src_vessel.withdrawal_height,
            tool=Instruments.PIPETTE,
        )
        toolkit.pump.withdraw(volume_to_withdraw=repetition_vol, solution=src_vessel)
        if isinstance(src_vessel, Well):
            toolkit.pump.withdraw(volume_to_withdraw=20)
        toolkit.mill.move_to_safe_position()
        toolkit.pump.withdraw(volume_to_withdraw=DRIP_STOP)

        if isinstance(src_vessel, StockVial):
            capping_sequence(
                toolkit.mill,
                Coordinates(src_vessel.x, src_vessel.y, src_vessel.top),
                toolkit.arduino,
            )

        if isinstance(dst_vessel, WasteVial):
            decapping_sequence(
                toolkit.mill,
                Coordinates(dst_vessel.x, dst_vessel.y, dst_vessel.top),
                toolkit.arduino,
            )

        toolkit.mill.safe_move(
            dst_vessel.x,
            dst_vessel.y,
            dst_vessel.top,
            tool=Instruments.PIPETTE,
        )
        toolkit.pump.infuse(
            volume_to_infuse=repetition_vol,
            being_infused=src_vessel,
            infused_into=dst_vessel,
            blowout_ul=(
                AIR_GAP + DRIP_STOP + 20
                if isinstance(src_vessel, Well)
                else AIR_GAP + DRIP_STOP
            ),
        )

        for _, vol in toolkit.pump.pipette.contents.items():
            if vol > 0.0:
                logger.warning("Pipette has residual volume of %f ul. Purging...", vol)
                toolkit.pump.infuse(
                    volume_to_infuse=vol,
                    being_infused=None,
                    infused_into=dst_vessel,
                    blowout_ul=vol,
                )

        if toolkit.pump.pipette.volume > 0.0:
            logger.warning(
                "Pipette has residual volume of %f ul. Purging...",
                toolkit.pump.pipette.volume,
            )
            toolkit.pump.infuse(
                volume_to_infuse=toolkit.pump.pipette.volume,
                being_infused=None,
                infused_into=dst_vessel,
                blowout_ul=toolkit.pump.pipette.volume,
            )
            toolkit.pump.pipette.volume = 0.0

        if isinstance(dst_vessel, WasteVial):
            capping_sequence(
                toolkit.mill,
                Coordinates(dst_vessel.x, dst_vessel.y, dst_vessel.top),
                toolkit.arduino,
            )


@timing_wrapper
def _forward_pipette_v3(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    dst_vessel: Union[Well, WasteVial],
    toolkit: Union[Toolkit, Hardware],
    source_concentration: float = None,
    labware: Optional[Labware] = None,
) -> int:
    try:
        if volume <= 0.0:
            return

        selected_source_vessels, source_vessel_volumes = _handle_source_vessels(
            volume=volume,
            src_vessel=src_vessel,
            source_concentration=source_concentration,
            pjct_logger=toolkit.global_logger,
        )

        for origin_vessel, _ in source_vessel_volumes:
            if isinstance(origin_vessel, Well) and isinstance(dst_vessel, StockVial):
                raise ValueError("Cannot pipette from a well to a stock vial")
            if isinstance(origin_vessel, WasteVial) and isinstance(dst_vessel, Well):
                raise ValueError("Cannot pipette from a waste vial to a well")
            if isinstance(origin_vessel, StockVial) and isinstance(
                dst_vessel, StockVial
            ):
                raise ValueError("Cannot pipette from a stock vial to a stock vial")

        for vessel, desired_volume in source_vessel_volumes:
            if desired_volume <= 0.0:
                continue
            _pipette_action(toolkit, vessel, dst_vessel, desired_volume)

    except Exception as e:
        toolkit.global_logger.error("Exception occurred during pipetting: %s", e)
        raise e
    return 0


# No timer wrapper for this function since its a wrapper itself
def transfer(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    dst_vessel: Union[Well, WasteVial],
    toolkit: Toolkit,
    source_concentration: float = None,
) -> int:
    """Transfer liquid between vessels.

    Parameters
    ----------
    volume : float
        Volume to transfer in microliters
    src_vessel : Union[str, Well, StockVial]
        Source vessel identifier or object
    dst_vessel : Union[Well, WasteVial]
        Destination vessel object
    toolkit : Toolkit
        Toolkit object for hardware control
    source_concentration : float, optional
        Target concentration in mM, by default None

    Returns
    -------
    int
        0 on success

    Notes
    -----
    This is a wrapper around _forward_pipette_v3 for more convenient usage
    """
    return _forward_pipette_v3(
        volume, src_vessel, dst_vessel, toolkit, source_concentration
    )


@timing_wrapper
def rinse_well(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    alt_sol_name: Optional[str] = None,
    alt_vol: Optional[float] = None,
    alt_count: Optional[int] = None,
) -> int:
    """Rinse a well with specified solution.

    Parameters
    ----------
    instructions : EchemExperimentBase
        Experiment instructions containing rinse parameters
    toolkit : Toolkit
        Toolkit object for hardware control
    alt_sol_name : str, optional
        Alternative solution name to use, by default None
    alt_vol : float, optional
        Alternative volume to use, by default None
    alt_count : int, optional
        Alternative rinse count to use, by default None

    Returns
    -------
    int
        0 on success

    Notes
    -----
    Performs multiple rinse cycles of pipetting solution in and out of the well
    """
    sol_name = instructions.rinse_sol_name if alt_sol_name is None else alt_sol_name
    vol = instructions.rinse_vol if alt_vol is None else alt_vol
    count = instructions.rinse_count if alt_count is None else alt_count

    logger.info(
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for _ in range(count):
        logger.info("Rinse %d of %d", _ + 1, count)
        # Pipette the rinse solution into the well
        _forward_pipette_v3(
            volume=vol,
            src_vessel=sol_name,
            dst_vessel=instructions.well,
            toolkit=toolkit,
        )

        # Clear the well
        _forward_pipette_v3(
            volume=vol,
            src_vessel=instructions.well,
            dst_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    return 0


@timing_wrapper
def flush_pipette(
    flush_with: str,
    toolkit: Toolkit,
    flush_volume: float = 120.0,
    flush_count: int = 1,
    instructions: Optional[ExperimentBase] = None,
):
    """
    Flush the pipette tip with the designated flush_volume ul to remove any residue
    Args:
        flush_solution_name (str): The name of the solution to flush with
        toolkit (Toolkit): The toolkit object
        flush_volume (float): The volume to flush with in microliters
        flush_count (int): The number of times to flush
        instructions (ExperimentBase): The experiment instructions for setting the status

    Returns:
        None (void function) since the objects are passed by reference
    """

    if flush_volume > 0.000:
        if instructions is not None:
            instructions.set_status_and_save(ExperimentStatus.FLUSHING)
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_with,
        )

        for _ in range(flush_count):
            _forward_pipette_v3(
                flush_volume,
                src_vessel=flush_with,
                dst_vessel=waste_selector("waste", flush_volume),
                toolkit=toolkit,
            )

        logger.debug(
            "Flushed pipette tip with %f ul of %s %dx times...",
            flush_volume,
            flush_with,
            flush_count,
        )
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0


@timing_wrapper
def purge_pipette(
    mill: Union[Mill, MockMill],
    pump: Union[SyringePump, MockPump],
):
    """
    Move the pipette over an available waste vessel and purge its contents

    Args:
        mill (Union[Mill, MockMill]): _description_
        pump (Union[Pump, MockPump]): _description_
    """
    liquid_volume = pump.pipette.liquid_volume()
    total_volume = pump.pipette.volume
    purge_vial = waste_selector("waste", liquid_volume)

    # Move to the purge vial
    mill.safe_move(
        purge_vial.x,
        purge_vial.y,
        purge_vial.top,
        tool=Instruments.PIPETTE,
    )

    # Purge the pipette
    pump.infuse(
        volume_to_infuse=liquid_volume,
        being_infused=None,
        infused_into=purge_vial,
        blowout_ul=total_volume - liquid_volume,
    )


@timing_wrapper
def volume_correction(
    volume: float, density: float = None, viscosity: float = None
) -> float:
    """
    Corrects the volume of the solution based on the density and viscosity of the solution

    Args:
        volume (float): The volume to be corrected
        density (float): The density of the solution
        viscosity (float): The viscosity of the solution

    Returns:
        corrected_volume (float): The corrected volume
    """
    if density is None:
        density = float(1.0)
    if viscosity is None:
        viscosity = float(1.0)
    corrected_volume = round(
        volume * (float(1.0) + (float(1.0) - density) * (float(1.0) - viscosity)), 6
    )
    return float(corrected_volume)


@timing_wrapper
def mix(
    toolkit: Union[Toolkit, Hardware],
    well: Well,
    volume: float,
    mix_count: int = 3,
    mix_height: float = None,
):
    """
    Mix the solution in the well by pipetting it up and down

    Args:
        toolkit (object): The toolkit object for hardware control
        well (Well, str): The well to be mixed
        volume (float): The volume to be mixed
        mix_count (int): The number of times to mix
        mix_height (float): The height to mix at
    """
    if mix_height is None:
        mix_height = well.well_data.bottom + well.well_data.height
    else:
        mix_height = well.well_data.bottom + mix_height

    if isinstance(well, str):
        well = toolkit.wellplate.get_well(well)

    logger.info("Mixing well %s %dx...", well.name, mix_count)

    # Withdraw air for blow out volume
    toolkit.pump.withdraw_air(40)

    for i in range(mix_count):
        logger.info("Mixing well %s %d of %d...", well.name, i + 1, mix_count)
        # Move to the bottom of the target well
        toolkit.mill.safe_move(
            x_coord=well.x,
            y_coord=well.y,
            z_coord=well.bottom,
            tool=Instruments.PIPETTE,
        )

        # Withdraw the solutions from the well
        toolkit.pump.withdraw(
            volume_to_withdraw=volume,
            solution=well,
            rate=toolkit.pump.max_pump_rate,
        )

        toolkit.mill.safe_move(
            x_coord=well.x,
            y_coord=well.y,
            z_coord=well.top,
            tool=Instruments.PIPETTE,
        )

        # Deposit the solution back into the well
        toolkit.pump.infuse(
            volume_to_infuse=volume,
            being_infused=None,
            infused_into=well,
            rate=toolkit.pump.max_pump_rate,
            blowout_ul=0,
        )

    toolkit.pump.infuse_air(40)
    toolkit.mill.move_to_safe_position()
    return 0


def clear_well(
    toolkit: Union[Toolkit, Hardware],
    well: Well,
):
    """
    Clear the well by pipetting the solution out of the well

    Args:
        toolkit (object): The toolkit object for hardware control
        well (Well, str): The well to be cleared
        volume (float): The volume to be cleared
    """
    if isinstance(well, str):
        well = toolkit.wellplate.get_well(well)

    logger.info("Clearing well %s...", well.name)

    transfer(
        volume=well.volume,
        src_vessel=well,
        dst_vessel=waste_selector("waste", well.volume),
        toolkit=toolkit,
    )
    return 0


if __name__ == "__main__":
    pass


# class PipettingOperations:
#     """Handles core pipetting operations."""

#     @staticmethod
#     def transfer(
#         volume: float,
#         src_vessel: Union[str, Well, StockVial],
#         dst_vessel: Union[Well, WasteVial],
#         toolkit: Toolkit,
#         source_concentration: Optional[float] = None,
#     ) -> int:
#         """Main transfer operation."""
#         # Move _forward_pipette_v3 here
#         pass

#     @staticmethod
#     def rinse_well(
#         instructions: EchemExperimentBase,
#         toolkit: Toolkit,
#         alt_sol_name: Optional[str] = None,
#         alt_vol: Optional[float] = None,
#         alt_count: Optional[int] = None,
#     ) -> int:
#         """Well rinsing operation."""
#         pass

#     @staticmethod
#     def flush_pipette(
#         flush_with: str,
#         toolkit: Toolkit,
#         flush_volume: float = 120.0,
#         flush_count: int = 1,
#         instructions: Optional[ExperimentBase] = None,
#     ) -> int:
#         """Pipette flushing operation."""
#         pass
