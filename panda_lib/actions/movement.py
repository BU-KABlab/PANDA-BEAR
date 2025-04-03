import asyncio
import logging
from logging import Logger
from pathlib import Path

from shared_utilities.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)

from ..labware import Vial, Well
from ..panda_gantry import PandaMill as Mill
from ..toolkit import ArduinoLink
from ..utilities import Coordinates

TESTING = read_testing_config()

if TESTING:
    pass
else:
    pass

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


def move_to_well(
    well: Well,
    mill: Mill,
    tool: str,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """Move the gantry to a specified well position.

    Parameters
    ----------
    well : Well
        The well object containing position information
    mill : Mill
        The mill controller object
    tool : str
        The tool identifier to move
    logger : Logger
        Logger for operation tracking
    z_offset : float, optional
        Additional Z-axis offset from well top, by default 0.0

    Notes
    -----
    Movement is performed using safe_move to avoid collisions
    """
    logger.info("Moving to well %s", well)
    mill.safe_move(well.x, well.y, well.top + z_offset, tool=tool)
    logger.info("Moved to well %s", well)


def move_to_vial(
    vial: Vial,
    mill: Mill,
    tool: str,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """Move the gantry to a specified vial position.

    Parameters
    ----------
    vial : Vial
        The vial object containing position information
    mill : Mill
        The mill controller object
    tool : str
        The tool identifier to move
    logger : Logger
        Logger for operation tracking
    z_offset : float, optional
        Additional Z-axis offset from vial top, by default 0.0

    Notes
    -----
    Movement is performed using safe_move to avoid collisions
    """
    logger.info("Moving to vial %s", vial)
    mill.safe_move(vial.coordinates.x, vial.coordinates.y, vial.top, tool=tool)
    logger.info("Moved to vial %s", vial)


def move_pipette_to_vial(
    vial: Vial,
    mill: Mill,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """Move pipette to specified vial position.

    Parameters
    ----------
    vial : Vial
        The vial object containing position information
    mill : Mill
        The mill controller object
    logger : Logger
        Logger for operation tracking
    z_offset : float, optional
        Additional Z-axis offset from vial top, by default 0.0

    Notes
    -----
    Uses pipette tool by default for movement
    """
    logger.info("Moving pipette to vial %s", vial)
    mill.safe_move(vial.coordinates.x, vial.coordinates.y, vial.top, tool="pipette")
    logger.info("Moved pipette to vial %s", vial)


def move_pipette_to_vial_bottom(
    vial: Vial,
    mill: Mill,
    logger: Logger,
) -> None:
    """Move pipette to bottom of specified vial.

    Parameters
    ----------
    vial : Vial
        The vial object containing position information
    mill : Mill
        The mill controller object
    logger : Logger
        Logger for operation tracking

    Notes
    -----
    Positions pipette at vial bottom for liquid handling
    """
    logger.info("Moving pipette to vial %s bottom", vial)
    mill.safe_move(vial.coordinates.x, vial.coordinates.y, vial.bottom, tool="pipette")
    logger.info("Moved pipette to vial %s bottom", vial)


def move_pipette_to_well(
    well: Well,
    mill: Mill,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """Move pipette to specified well position.

    Parameters
    ----------
    well : Well
        The well object containing position information
    mill : Mill
        The mill controller object
    logger : Logger
        Logger for operation tracking
    z_offset : float, optional
        Additional Z-axis offset from well top, by default 0.0

    Notes
    -----
    Uses pipette tool by default for movement
    """
    logger.info("Moving pipette to well %s", well)
    mill.safe_move(well.x, well.y, well.top + z_offset, tool="pipette")
    logger.info("Moved pipette to well %s", well)


def move_pipette_to_well_bottom(
    well: Well,
    mill: Mill,
    logger: Logger,
) -> None:
    """
    Move the pipette to the specified well.

    Args:
        well (Well): The well to move to.
        mill (Mill): The mill object.
        toolkit (Toolkit): The toolkit object.
        logger (Logger): The logger object.
        z_offset (float): The z-axis offset from the top.
    """
    # Move to the well
    logger.info(f"Moving pipette to well {well}")
    mill.safe_move(well.x, well.y, well.bottom, tool="pipette")
    logger.info(f"Moved pipette to well {well}")


def move_electrode_to_well(
    well: Well,
    mill: Mill,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """
    Move the electrode to the specified well.

    Args:
        well (Well): The well to move to.
        mill (Mill): The mill object.
        toolkit (Toolkit): The toolkit object.
        logger (Logger): The logger object.
        z_offset (float): The z-axis offset from the top.
    """
    # Move to the well
    logger.info(f"Moving electrode to well {well}")
    mill.safe_move(well.x, well.y, well.top + z_offset, tool="electrode")
    logger.info(f"Moved electrode to well {well}")


def move_electrode_to_well_bottom(
    well: Well,
    mill: Mill,
    logger: Logger,
) -> None:
    """
    Move the electrode to the specified well.

    Args:
        well (Well): The well to move to.
        mill (Mill): The mill object.
        toolkit (Toolkit): The toolkit object.
        logger (Logger): The logger object.
        z_offset (float): The z-axis offset from the top.
    """
    # Move to the well
    logger.info(f"Moving electrode to well {well}")
    mill.safe_move(well.x, well.y, well.bottom, tool="electrode")
    logger.info(f"Moved electrode to well {well}")


def move_electrode_to_vial(
    vial: Vial,
    mill: Mill,
    logger: Logger,
    z_offset: float = 0.0,
) -> None:
    """
    Move the electrode to the specified vial.

    Args:
        vial (Vial): The vial to move to.
        mill (Mill): The mill object.
        toolkit (Toolkit): The toolkit object.
        logger (Logger): The logger object.
        z_offset (float): The z-axis offset from the top.
    """
    # Move to the vial
    logger.info(f"Moving electrode to vial {vial}")
    mill.safe_move(vial.coordinates.x, vial.coordinates.y, vial.top, tool="electrode")
    logger.info(f"Moved electrode to vial {vial}")


def move_electrode_to_vial_bottom(
    vial: Vial,
    mill: Mill,
    logger: Logger,
) -> None:
    """
    Move the electrode to the specified vial.

    Args:
        vial (Vial): The vial to move to.
        mill (Mill): The mill object.
        toolkit (Toolkit): The toolkit object.
        logger (Logger): The logger object.
        z_offset (float): The z-axis offset from the top.
    """
    # Move to the vial
    logger.info(f"Moving electrode to vial {vial}")
    mill.safe_move(
        vial.coordinates.x, vial.coordinates.y, vial.bottom, tool="electrode"
    )
    logger.info(f"Moved electrode to vial {vial}")


def decapping_sequence(
    mill: Mill, target_coords: Coordinates, ard_link: ArduinoLink
) -> None:
    """Execute vial decapping sequence.

    Parameters
    ----------
    mill : Mill
        The mill controller object
    target_coords : Coordinates
        Target coordinates for decapping operation
    ard_link : ArduinoLink
        Arduino interface for cap control

    Notes
    -----
    Sequence steps:
    1. Move to target coordinates
    2. Activate decapper
    3. Move decapper up to 0mm Z position
    4. Check that a cap is present by checking the line break sensor
       (should be true - broken line and cap present)
    """
    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Activate the decapper
    ard_link.no_cap()

    # Move the decapper up to 0
    mill.move_to_position(
        target_coords.x,
        target_coords.y,
        0,
        tool="decapper",
    )

    unit_version = config.get("PANDA", "unit_version")
    # Check that a cap is present by checking the line break sensor (should be true - broken line and cap present)
    if unit_version > 1.0:
        line_break_result = asyncio.run(ard_link.async_line_break())
        if not line_break_result:
            raise ValueError("Cap is not present on decapper after decapping operation")
    else:
        # For unit versions <= 1.0, we assume the cap is present
        # as the line break sensor is not available
        pass

def capping_sequence(
    mill: Mill, target_coords: Coordinates, ard_link: ArduinoLink
) -> None:
    """Execute vial capping sequence.

    Parameters
    ----------
    mill : Mill
        The mill controller object
    target_coords : Coordinates
        Target coordinates for capping operation
    ard_link : ArduinoLink
        Arduino interface for cap control

    Notes
    -----
    Sequence steps:
    1. Move to target coordinates
    2. Deactivate decapper
    3. Move decapper +15mm in Y direction
    4. Move decapper to 0mm Z position
    5. Check that a cap is present by checking the line break sensor
       (should be false - no cap present)
    """
    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Deactivate the decapper
    ard_link.ALL_CAP()

    # Move the decapper +10mm in the y direction
    mill.move_to_position(target_coords.x, target_coords.y + 15, 0, tool="decapper")

    unit_version = config.get("PANDA", "unit_version")
    # Check that a cap is present by checking the line break sensor (should be false - no cap present)
    if unit_version > 1.0:
        line_break_result = asyncio.run(ard_link.async_line_break())
        if line_break_result:
            raise ValueError("Cap is still present after capping operation")
    else:
        # For unit versions <= 1.0, we assume the cap is not present
        # as the line break sensor is not available
        pass

if __name__ == "__main__":
    pass
