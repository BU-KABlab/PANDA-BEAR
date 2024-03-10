"""
Responsible for calling the appropirate interfaces to perform a given experiment.

Args:
    Expriment instructions : Experiment
        All parameters to run the experiment
    Mill: Mill object
    Pump: Pump object
    Potentiostat: Potentiostat object
    Camera: Camera object
    OBS: OBS object
    Wellplate: Wellplate object
    Vials: Vials object
    Scale: Scale object

Returns:
    ExperimentResult: The results of the experiment.
    Wellplate: The updated wellplate object.
    Vials: The updated vials object.
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, broad-exception-caught

# Standard library imports
import logging
import math

# import decimal

# Third party or custom imports
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from epanda_lib import instrument_toolkit
from epanda_lib.camera_call_camera import capture_new_image
from epanda_lib.config.config import (
    AIR_GAP,
    DRIP_STOP,
    PATH_TO_DATA,
    PATH_TO_LOGS,
    PURGE_VOLUME,
    TESTING,
)
from epanda_lib.experiment_class import ExperimentBase,EchemExperimentBase, ExperimentResult, ExperimentStatus
from epanda_lib.log_tools import CustomLoggingFilter
from epanda_lib.mill_control import Instruments, Mill, MockMill
from epanda_lib.pump_control import MockPump, Pump
from epanda_lib.vials import StockVial, WasteVial
from epanda_lib.wellplate import Well, Wellplate
from epanda_lib.correction_factors import correction_factor
from epanda_lib.instrument_toolkit import Toolkit

# import gamry_control_WIP as echem
# from gamry_control_WIP import (potentiostat_ocp_parameters)

if TESTING:
    from epanda_lib.gamry_control_WIP_mock import GamryPotentiostat as echem
    from epanda_lib.gamry_control_WIP_mock import potentiostat_ocp_parameters
else:
    import epanda_lib.gamry_control_WIP as echem
    from epanda_lib.gamry_control_WIP import potentiostat_ocp_parameters

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger("e_panda")
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter(
    "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s"
)
system_handler = logging.FileHandler(PATH_TO_LOGS / "ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

# Add a testing logger
testing_logger = logging.getLogger("testing")
testing_logger.setLevel(logging.DEBUG)
testing_handler = logging.FileHandler(PATH_TO_LOGS / "testing.log")
testing_handler.setFormatter(formatter)
testing_logger.addHandler(testing_handler)


def forward_pipette_v2(
    volume: float,
    from_vessel: Union[Well, StockVial, WasteVial],
    to_vessel: Union[Well, WasteVial],
    pump: Union[Pump, MockPump],
    mill: Union[Mill, MockMill],
    pumping_rate: Optional[float] = None,
):
    """
    Pipette a volume from one vessel to another

    Depending on the supplied vessels, this function will perform one of the following:
    1. Pipette from a stock vial to a well
    2. Pipette from a well to a waste vial*
    3. Pipette from a stock vial to a waste vial*
        * When pipetting to a waste vial the dispesnsing height will be above the solution depth to avoid contamination

    It will not allow:
    1. Pipetting from a waste vial to a well
    2. Pipetting from a well to a stock vial
    3. Pipetting from a stock vial toa  stock vial

    The steps that this function will perform:
    1. Determine the number of repetitions
    2. Withdraw the solution from the source
        a. Withdraw an air gap to engage the screw
        b. Move to the source
        c. Withdraw the solution
        d. Move back to safe height
        e. Withdraw an air gap to prevent dripping
    3. Deposit the solution into the destination vessel
        a. Move to the destination
        b. Deposit the solution and blow out
        c. Move back to safe height
        d. If depositing stock solution into a well, the recorded weight change will be saved to the target well
            in the wellplate object and the stock vial object will be updated with a corrected new volume based on the density of the solution.
    4. Repeat 2-3 until all repetitions are complete

    Args:
        volume (float): The volume to be pipetted in microliters
        from_vessel (Vial or Well): The vessel object to be pipetted from (must be selected before calling this function)
        to_vessel (Vial or Well): The vessel object to be pipetted to (must be selected before calling this function)
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        mill (object): The mill object
        wellplate (Wells object): The wellplate object

    Returns:
        None (void function) since the objects are passed by reference

    """
    if volume > 0.00:
        logger.info(
            "Forward pipetting %f ul from %s to %s",
            volume,
            from_vessel.name,
            to_vessel.name,
        )
        # Check to ensure that the from_vessel and to_vessel are an allowed combination
        if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a well to a stock vial")
        elif isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
            raise ValueError("Cannot pipette from a waste vial to a well")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a stock vial to a stock vial")

        # Calculate the number of repetitions
        # based on pipette capacity and drip stop
        if pumping_rate is None:
            pumping_rate = pump.max_pump_rate

        repetitions = math.ceil(volume / (pump.pipette.capacity_ul - DRIP_STOP))
        repetition_vol = round(volume / repetitions, 6)

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engage screw receive nothing
            pump.withdraw(
                volume=AIR_GAP, solution=None, rate=pump.max_pump_rate
            )  # withdraw air gap to engage screw

            if isinstance(from_vessel, Well):
                logger.info(
                    "Moving to %s at %s...", from_vessel.name, from_vessel.coordinates
                )
                from_vessel: Well = from_vessel
                mill.safe_move(
                    from_vessel.coordinates["x"],
                    from_vessel.coordinates["y"],
                    from_vessel.depth,
                    Instruments.PIPETTE,
                )
            else:
                logger.info(
                    "Moving to %s at %s...", from_vessel.name, from_vessel.position
                )
                mill.safe_move(
                    from_vessel.coordinates["x"],
                    from_vessel.coordinates["y"],
                    from_vessel.depth,
                    Instruments.PIPETTE,
                )  # go to solution depth

            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol,
                solution=from_vessel,
                rate=pumping_rate,
                weigh=False,
            )  # pipette now has air gap + repetition vol

            if isinstance(from_vessel, Well):
                pump.withdraw(
                    volume=20, solution=None, rate=pump.max_pump_rate, weigh=False
                )  # If the from vessel is a well withdraw a little extra to ensure cleared well

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pump.max_pump_rate, weigh=False
            )

            logger.debug(
                "From Vessel %s volume: %f depth: %f",
                from_vessel.name,
                from_vessel.volume,
                from_vessel.depth,
            )

            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)

            if isinstance(to_vessel, Well):
                to_vessel: Well = to_vessel
            else:
                to_vessel: WasteVial = to_vessel

            mill.safe_move(
                to_vessel.coordinates.x,
                to_vessel.coordinates.y,
                to_vessel.coordinates.z_top,
                Instruments.PIPETTE,
            )

            weigh = bool(isinstance(to_vessel, Well))

            # Infuse into the
            ## Testing
            blow_out = (
                AIR_GAP + DRIP_STOP + 20
                if isinstance(from_vessel, Well)
                else AIR_GAP + DRIP_STOP
            )
            is_pipette_volume_equal = pump.pipette.volume >= blow_out
            testing_logger.debug(
                "TESTING: Is pipette volume greater than or equal to blowout? %s",
                is_pipette_volume_equal,
            )

            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pump.max_pump_rate,
                blowout_ul=(
                    AIR_GAP + DRIP_STOP + 20
                    if isinstance(from_vessel, Well)
                    else AIR_GAP + DRIP_STOP
                ),
                weigh=weigh,
            )

            #mill.move_to_safe_position()


def reverse_pipette_v2(
    volume: float,
    from_vessel: Union[Well, StockVial, WasteVial],
    to_vessel: Union[Well, WasteVial],
    purge_vessel: WasteVial,
    pump: Union[Pump, MockPump],
    mill: Union[Mill, MockMill],
    pumping_rate: Optional[float] = None,
):
    """
    Reverse Pipette a volume from one vessel to another.

    Depending on the supplied vessels, this function will perform one of the following:
    1. Pipette from a stock vial to a well
    2. Pipette from a well to a waste vial*
    3. Pipette from a stock vial to a waste vial*
        * When pipetting to a waste vial the dispesnsing height will be above the solution depth to avoid contamination

    It will not allow:
    1. Pipetting from a waste vial to a well
    2. Pipetting from a well to a stock vial
    3. Pipetting from a stock vial toa  stock vial

    The steps that this function will perform:
    1. Determine the number of repetitions
    2. Withdraw the solution from the source
        a. Withdraw an air gap to engage the screw
        b. Move to the source
        c. Withdraw the solution volume + purge volume
        d. Move back to safe height
        e. Withdraw an air gap to prevent dripping
    3. Deposit the solution into the destination vessel
        a. Move to the destination
        b. Deposit the solution and blow out
        c. Move to the purge vessel
        d. Purge the purge volume
        If depositing stock solution into a well, the recorded weight change will be saved to the target well
        in the wellplate object and the stock vial object will be updated with a corrected new volume based on the density of the solution.
    4. Repeat 2-3 until all repetitions are complete

    Args:
        volume (float): The volume to be pipetted in microliters
        from_vessel (Vial or Well): The vessel object to be pipetted from (must be selected before calling this function)
        to_vessel (Vial or Well): The vessel object to be pipetted to (must be selected before calling this function)
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        mill (object): The mill object
        wellplate (Wells object): The wellplate object

    Returns:
        None (void function) since the objects are passed by reference

    """
    purge_volume = PURGE_VOLUME
    if volume > 0.00:
        logger.info(
            "Reverse pipetting %f ul from %s to %s",
            volume,
            from_vessel.name,
            to_vessel.name,
        )
        # Check to ensure that the from_vessel and to_vessel are an allowed combination
        if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a well to a vial")
        elif isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
            raise ValueError("Cannot pipette from a waste vial to a well")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a stock vial to a stock vial")

        # Calculate the number of repetitions
        # based on pipette capacity and drip stop
        if pumping_rate is None:
            pumping_rate = pump.max_pump_rate

        repetitions = math.ceil(
            volume / (pump.pipette.capacity_ul - DRIP_STOP - purge_volume)
        )
        repetition_vol = volume / repetitions

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engange screw receive nothing
            pump.withdraw(
                volume=AIR_GAP, solution=None, rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", from_vessel.name)
            mill.safe_move(
                from_vessel.coordinates.x,
                from_vessel.coordinates.y,
                from_vessel.coordinates.z_bottom,  # from_vessel.depth,
                Instruments.PIPETTE,
            )  # go to solution depth (depth replaced with height)

            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol + purge_volume,
                solution=from_vessel,
                rate=pumping_rate,
                weigh=False,
            )  # pipette now has air gap + repitition vol + purge volume

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )  # pipette now has air gap + repitition vol + purge volume + drip stop

            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)
            # determine if the destination is a well or a waste vial
            if isinstance(to_vessel, Well):  # go to solution depth
                logger.debug("%s is a Well", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    0,
                    Instruments.PIPETTE,
                )
                logger.info("Moved to well %s", to_vessel.name)
            else:  # go to safe height above vial
                logger.debug("%s is a Vial", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates.x,
                    to_vessel.coordinates.y,
                    from_vessel.coordinates.z_bottom,  # to_vessel.depth + 5 ,
                    Instruments.PIPETTE,
                )
                logger.info("Moved to vial %s", to_vessel.name)

            # Infuse into the to_vessel and receive the updated vessel object
            logger.info("Infusing %s into %s", from_vessel.name, to_vessel.name)
            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pumping_rate,
                blowout_ul=DRIP_STOP,
                weigh=True,
            )  # pipette now has purge volume
            logger.info(
                "Infused %s into %s. Moving to safe position",
                from_vessel.name,
                to_vessel.name,
            )
            mill.move_to_safe_position()
            logger.info("Moved to safe position")
            # Update the contentes of the to_vessel
            logger.debug("Updating contents of %s", to_vessel.name)
            to_vessel.update_contents(from_vessel.name, repetition_vol)

            logger.info(
                "Vessel %s volume: %f",
                to_vessel.name,
                to_vessel.volume,
            )
            logger.info("Withdrawing the drip stop...")
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )  # pipette now has purge volume + air gap + drip stop
            logger.info("Moving to purge vial %s...", purge_vessel.name)
            mill.safe_move(
                purge_vessel.coordinates.x,
                purge_vessel.coordinates.y,
                purge_vessel.coordinates.z_top,
                Instruments.PIPETTE,
            )
            logger.info("Purging the purge volume")
            pump.infuse(
                volume_to_infuse=purge_volume,
                being_infused=from_vessel,
                infused_into=purge_vessel,
                rate=pumping_rate,
                blowout_ul=DRIP_STOP + AIR_GAP,
                weigh=False,  # Vials are not on the scale
            )  # Pipette should be empty after this
            logger.info(
                "Purged the purge volume, updating contents of %s - %s",
                purge_vessel.position,
                purge_vessel.name,
            )
            purge_vessel.update_contents(from_vessel.name, purge_volume)

            mill.move_to_safe_position()


def rinse_v2(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Rinse the well with rinse_vol ul.
    Involves pipetteing and then clearing the well with no purging steps

    Args:
        instructions (Experiment): The experiment instructions
        toolkit (Toolkit): The toolkit object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
    Returns:
        None (void function) since the objects are passed by reference
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    instructions.set_status(ExperimentStatus.RINSING)
    for _ in range(instructions.rinse_count):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(instructions.rinse_vol),
            from_vessel=solution_selector(
                stock_vials,
                "rinse",
                correction_factor(instructions.rinse_vol),
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=toolkit.pump.max_pump_rate,
        )
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.PIPETTE,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(instructions.rinse_vol),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                correction_factor(instructions.rinse_vol),
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
        )
    return 0


def clear_well(
    volume: float,
    from_vessel: Well,
    to_vessel: WasteVial,
    pump: Union[Pump, MockPump],
    mill: Union[Mill, MockMill],
    pumping_rate: Optional[float] = None,
):
    """
    Pipette a volume from a well to waste vessel. This is used to clear the well of any remaining solution.

    This fuction will only allow pipetting from a well to a waste vial.

    The volume to be cleared is given, and the function will calculate the number of repetitions based on the pipette capacity and drip stop.
    During a repetition, the function will:
    1. Withdraw the solution from the well
        a. Withdraw an air gap to engage the screw
        b. Move the pipette to 1.5mm to the left of center of the well
        c. Withdraw the 1/2 of the repetition volume
        d. Move the pipette to 1.5mm to the right of center of the well
        e. Withdraw the 1/2 of the repetition volume
        f. Withdraw an air gap to prevent dripping
    2. Deposit the solution into the destination vessel
        a. Move to the destination
        b. Deposit the solution and blow out
        c. Move back to safe height
    3. Repeat 1-2 until all repetitions are complete

    Args:
        volume (float): The volume to be pipetted in microliters
        from_vessel (Vial or Well): The vessel object to be pipetted from (must be selected before calling this function)
        to_vessel (Vial or Well): The vessel object to be pipetted to (must be selected before calling this function)
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        mill (object): The mill object
        wellplate (Wells object): The wellplate object

    Returns:
        None (void function) since the objects are passed by reference

    """
    if volume > 0.00:
        logger.info(
            "Forward pipetting %f ul from %s to %s",
            volume,
            from_vessel.name,
            to_vessel.name,
        )
        # Check to ensure that the from_vessel and to_vessel are an allowed combination
        if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a well to a stock vial")
        elif isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
            raise ValueError("Cannot pipette from a waste vial to a well")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a stock vial to a stock vial")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, WasteVial):
            raise ValueError(
                "Clear_well function may not pipette from a stock vial to a waste vial"
            )

        # Calculate the number of repetitions
        # based on pipette capacity and drip stop
        if pumping_rate is None:
            pumping_rate = pump.max_pump_rate

        repetitions = math.ceil(volume / (pump.pipette.capacity_ul - DRIP_STOP))
        repetition_vol = round(volume / repetitions, 6)

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engage screw receive nothing
            pump.withdraw(
                volume=AIR_GAP, solution=None, rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info(
                "Moving to %s at %s...", from_vessel.name, from_vessel.coordinates
            )
            mill.safe_move(
                from_vessel.coordinates["x"],
                from_vessel.coordinates["y"],
                from_vessel.depth,
                Instruments.PIPETTE,
            )

            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol,
                solution=from_vessel,
                rate=pumping_rate,
                weigh=False,
            )  # pipette now has air gap + repetition vol

            if isinstance(from_vessel, Well):
                pump.withdraw(
                    volume=20, solution=None, rate=pumping_rate, weigh=False
                )  # If the from vessel is a well withdraw a little extra to ensure cleared well

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )

            logger.debug(
                "From Vessel %s volume: %f depth: %f",
                from_vessel.name,
                from_vessel.volume,
                from_vessel.depth,
            )

            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)

            if isinstance(to_vessel, Well):
                to_vessel: Well = to_vessel
            else:
                to_vessel: WasteVial = to_vessel

            mill.safe_move(
                to_vessel.coordinates.x,
                to_vessel.coordinates.y,
                to_vessel.coordinates.z_top,
                Instruments.PIPETTE,
            )

            weigh = bool(isinstance(to_vessel, Well))

            # Infuse into the
            ## Testing
            blow_out = (
                AIR_GAP + DRIP_STOP + 20
                if isinstance(from_vessel, Well)
                else AIR_GAP + DRIP_STOP
            )
            is_pipette_volume_equal = pump.pipette.volume >= blow_out
            testing_logger.debug(
                "TESTING: Is pipette volume greater than or equal to blowout? %s",
                is_pipette_volume_equal,
            )

            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pumping_rate,
                blowout_ul=(
                    AIR_GAP + DRIP_STOP + 20
                    if isinstance(from_vessel, Well)
                    else AIR_GAP + DRIP_STOP
                ),
                weigh=weigh,
            )

            mill.move_to_safe_position()


def flush_v2(
    waste_vials: Sequence[WasteVial],
    stock_vials: Sequence[StockVial],
    flush_solution_name: str,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    pumping_rate=0.5,
    flush_volume=120,
    flush_count=1,
    instructions: Optional[ExperimentBase] = None,
):
    """
    Flush the pipette tip with the designated flush_volume ul of DMF to remove any residue
    Args:
        waste_vials (list): The list of waste vials
        stock_vials (list): The list of stock vials
        flush_solution_name (str): The name of the solution to flush with
        mill (object): The mill object
        pump (object): The pump object
        pumping_rate (float): The pumping rate in ml/min
        flush_volume (float): The volume to flush with in microliters
        flush_count (int): The number of times to flush

    Returns:
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
    """

    if flush_volume > 0.000:
        if instructions is not None:
            instructions.set_status(ExperimentStatus.FLUSHING)
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_solution_name,
        )
        flush_solution = solution_selector(
            stock_vials, flush_solution_name, flush_volume
        )
        waste_vial = waste_selector(waste_vials, "waste", flush_volume)

        for _ in range(flush_count):
            forward_pipette_v2(
                flush_volume,
                from_vessel=flush_solution,
                to_vessel=waste_vial,
                pump=pump,
                mill=mill,
                pumping_rate=pumping_rate,
            )

        logger.info(
            "Flushed pipette tip with %f ul of %s %dx times...",
            flush_volume,
            flush_solution_name,
            flush_count,
        )
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0


def purge_pipette(
    waste_vials: Sequence[WasteVial],
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
):
    """
    Move the pipette over an available waste vessel and purge its contents

    Args:
        waste_vials (Sequence[WasteVial]): _description_
        mill (Union[Mill, MockMill]): _description_
        pump (Union[Pump, MockPump]): _description_
    """
    liquid_volume = pump.pipette.liquid_volume()
    total_volume = pump.pipette.volume
    purge_vial = waste_selector(waste_vials, "waste", liquid_volume)

    # Move to the purge vial
    mill.safe_move(
        purge_vial.coordinates.x,
        purge_vial.coordinates.y,
        purge_vial.coordinates.z_top,
        Instruments.PIPETTE,
    )

    # Purge the pipette
    pump.infuse(
        volume_to_infuse=liquid_volume,
        being_infused=None,
        infused_into=purge_vial,
        blowout_ul=total_volume - liquid_volume,
    )


def solution_selector(
    solutions: Sequence[StockVial], solution_name: str, volume: float
) -> StockVial:
    """
    Select the solution from which to withdraw from, from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    for solution in solutions:
        # if the solution names match and the requested volume is less than the available volume (volume - 15% of capacity)
        if (
            solution.name.lower() == solution_name.lower()
            and solution.volume - 0.10 * solution.capacity > (volume)
        ):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


def waste_selector(
    solutions: Sequence[WasteVial], solution_name: str, volume: float
) -> WasteVial:
    """
    Select the solution in which to deposit into from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    solution_name = solution_name.lower()
    for waste_solution in solutions:
        if (
            waste_solution.name.lower() == solution_name
            and (waste_solution.volume + volume) < waste_solution.capacity
        ):
            logger.debug(
                "Selected waste vial: %s in position %s",
                waste_solution.name,
                waste_solution.position,
            )
            return waste_solution
    raise NoAvailableSolution(solution_name)


def chrono_amp(
    dep_instructions: EchemExperimentBase,
    file_tag: str = None,
) -> Tuple[EchemExperimentBase, ExperimentResult]:
    """
    Deposition of the solutions onto the substrate. This includes the OCP and CA steps.

    No pipetting is performed in this step.

    Args:
        dep_instructions (Experiment): The experiment instructions
        dep_results (ExperimentResult): The experiment results
        mill (object): The mill object
        wellplate (Wells object): The wellplate object
    Returns:
        dep_instructions (Experiment): The updated experiment instructions
        dep_results (ExperimentResult): The updated experiment results
    """
    try:
        # echem setup
        logger.info("Setting up eChem deposition experiments...")

        if TESTING:
            pstat = echem()
        else:
            pstat = echem
        pstat.pstatconnect()

        # echem OCP
        logger.info("Beginning eChem OCP of well: %s", dep_instructions.well_id)
        dep_instructions.set_status(ExperimentStatus.OCPCHECK)

        base_filename = pstat.setfilename(
            dep_instructions.id,
            file_tag + "_OCP_CA" if file_tag else "OCP_CA",
            dep_instructions.project_id,
            dep_instructions.project_campaign_id,
            dep_instructions.well_id,
        )
        dep_results = dep_instructions.results
        dep_results.ocp_dep_files.append(base_filename)
        pstat.OCP(
            potentiostat_ocp_parameters.OCPvi,
            potentiostat_ocp_parameters.OCPti,
            potentiostat_ocp_parameters.OCPrate,
        )  # OCP
        pstat.activecheck()
        ocp_dep_pass, ocp_char_final_voltage = pstat.check_vf_range(
            dep_results.ocp_dep_files[-1].with_suffix(".txt")
        )
        dep_results.ocp_dep_passes.append(ocp_dep_pass)
        dep_results.ocp_char_final_voltages.append(ocp_char_final_voltage)
        # plotdata("OCP", dep_results.ocp_dep_file.with_suffix(".txt"))

        # echem CA - deposition
        if dep_results.ocp_dep_passes[-1]:
            try:
                dep_instructions.set_status(ExperimentStatus.EDEPOSITING)
                logger.info(
                    "Beginning eChem deposition of well: %s", dep_instructions.well_id
                )
                dep_results.deposition_data_files.append(
                    pstat.setfilename(
                        dep_instructions.id,
                        file_tag + "_CA" if file_tag else "CA",
                        dep_instructions.project_id,
                        dep_instructions.project_campaign_id,
                        dep_instructions.well_id,
                    )
                )

                # FEATURE have chrono return the max and min values for the deposition
                # and save them to the results
                # don't have any parameters hardcoded, switch these all to instructions
                pstat.chrono(
                    CAvi=dep_instructions.ca_prestep_voltage,
                    CAti=dep_instructions.ca_prestep_time_delay,
                    CAv1=dep_instructions.ca_step_1_voltage,
                    CAt1=dep_instructions.ca_step_1_time,
                    CAv2=dep_instructions.ca_step_2_voltage,
                    CAt2=dep_instructions.ca_step_2_time,
                    CAsamplerate=dep_instructions.ca_sample_period,
                )  # CA

                pstat.activecheck()
                # plotdata("CA", dep_results.deposition_data_file.with_suffix(".txt"))
            except Exception as e:
                logger.error("Exception occurred during deposition: %s", e)
                raise CAFailure(dep_instructions.id, dep_instructions.well_id) from e
        else:
            raise OCPFailure("CA")
    except Exception as e:
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(dep_instructions.id, dep_instructions.well_id) from e
    finally:
        pstat.pstatdisconnect()
    return dep_instructions, dep_results


def cyclic_volt(
    char_instructions: EchemExperimentBase, file_tag: str = None
) -> Tuple[EchemExperimentBase, ExperimentResult]:
    """
    Characterization of the solutions on the substrate using CV.
    No pipetting is performed in this step.
    Rinse the electrode after characterization.

    Args:
        char_instructions (Experiment): The experiment instructions

    Returns:
        char_instructions (Experiment): The updated experiment instructions
        char_results (ExperimentResult): The updated experiment results
    """
    try:
        logger.info("Characterizing well: %s", char_instructions.well_id)
        # echem OCP
        logger.info("Beginning eChem OCP of well: %s", char_instructions.well_id)
        if TESTING:
            pstat = echem()
        else:
            pstat = echem
        pstat.pstatconnect()
        char_instructions.set_status(ExperimentStatus.OCPCHECK)
        char_instructions.results.ocp_char_files.append(
            pstat.setfilename(
                char_instructions.id,
                file_tag + "_OCP_CV" if file_tag else "OCP_CV",
                char_instructions.project_id,
                char_instructions.project_campaign_id,
                char_instructions.well_id,
            )
        )
        pstat.OCP(
            OCPvi=potentiostat_ocp_parameters.OCPvi,
            OCPti=potentiostat_ocp_parameters.OCPti,
            OCPrate=potentiostat_ocp_parameters.OCPrate,
        )  # OCP
        pstat.activecheck()
        (
            ocp_char_pass,
            char_instructions.cv_initial_voltage,
        ) = pstat.check_vf_range(
            char_instructions.results.ocp_char_files[-1].with_suffix(".txt")
        )
        char_instructions.results.ocp_char_passes.append(ocp_char_pass)
        logger.info(
            "OCP of well %s passed: %s",
            char_instructions.well_id,
            char_instructions.results.ocp_char_passes[-1],
        )
    except Exception as e:
        logger.error("Exception occurred during OCP: %s", e)
        pstat.pstatdisconnect()
        raise OCPFailure("characterization") from e

    if char_instructions.results.ocp_char_passes[-1]:
        try:
            # echem CV - characterization
            if char_instructions.baseline == 1:
                test_type = "CV_baseline"
                char_instructions.set_status(ExperimentStatus.BASELINE)
            else:
                test_type = "CV"
                char_instructions.set_status(ExperimentStatus.CHARACTERIZING)

            logger.info(
                "Beginning eChem %s of well: %s", test_type, char_instructions.well_id
            )

            char_instructions.results.characterization_data_files.append(
                pstat.setfilename(
                    char_instructions.id,
                    file_tag + "_CV" if file_tag else test_type,
                    char_instructions.project_id,
                    char_instructions.project_campaign_id,
                    char_instructions.well_id,
                )
            )

            # FEATURE have cyclic return the max and min values for the characterization
            # and save them to the results
            pstat.cyclic(
                CVvi=char_instructions.cv_initial_voltage,
                CVap1=char_instructions.cv_first_anodic_peak,
                CVap2=char_instructions.cv_second_anodic_peak,
                CVvf=char_instructions.cv_final_voltage,
                CVsr1=char_instructions.cv_scan_rate_cycle_1,
                CVsr2=char_instructions.cv_scan_rate_cycle_2,
                CVsr3=char_instructions.cv_scan_rate_cycle_3,
                CVsamplerate=char_instructions.cv_sample_rate,
                CVcycle=char_instructions.cv_cycle_count,
            )
            pstat.activecheck()
            # plotdata("CV", char_results.characterization_data_file.with_suffix(".txt"))
        except Exception as e:
            logger.error("Exception occurred during CV: %s", e)
            pstat.pstatdisconnect()
            raise CVFailure(char_instructions.id, char_instructions.well_id) from e

    pstat.pstatdisconnect()
    return char_instructions


def apply_log_filter(
    experiment_id: int = None,
    target_well: Optional[str] = None,
    campaign_id: Optional[str] = None,
    test: bool = TESTING,
):
    """Add custom value to log format"""
    experiment_formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s&%(custom4)s"
    )
    system_handler.setFormatter(experiment_formatter)
    custom_filter = CustomLoggingFilter(campaign_id, experiment_id, target_well, test)
    logger.addFilter(custom_filter)


def volume_correction(volume, density=None, viscosity=None):
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
        density = 1.0
    if viscosity is None:
        viscosity = 1.0
    corrected_volume = volume * (1.0 + (1.0 - density) * (1.0 - viscosity))
    return corrected_volume


def image_well(
    toolkit: instrument_toolkit.Toolkit,
    instructions: EchemExperimentBase = None,
    step_description: str = None,
):
    """
    Image the well with the camera

    Args:
        toolkit (Toolkit): The toolkit object
        instructions (Experiment): The experiment instructions
        step_description (str): The description of the step

    Returns:
        None (void function) since the objects are passed by reference
    """
    try:
        instructions.set_status(ExperimentStatus.IMAGING)
        logger.info("Imaging well %s", instructions.well_id)
        # capture image
        logger.debug("Capturing image of well %s", instructions.well_id)

        # create file name
        project_campaign_id = instructions.project_campaign_id or "test"
        project_id = instructions.project_id or "test"
        exp_id = instructions.id or "test"
        well_id = instructions.well_id or "test"

        if step_description is not None:
            file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_{step_description}_image"
        else:
            file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_image"
        file_name = file_name.replace(" ", "_")  # clean up the file name
        file_name_start = file_name + "_0"  # enumerate the file name
        filepath = Path(PATH_TO_DATA / str(file_name_start)).with_suffix(".png")
        i = 1
        while filepath.exists():
            next_file_name = f"{file_name}_{i}"
            filepath = Path(PATH_TO_DATA / str(next_file_name)).with_suffix(".png")
            i += 1

        # position lens above the well
        logger.info("Moving camera above well %s", well_id)
        if well_id != "test":
            toolkit.mill.safe_move(
                toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
                toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
                toolkit.wellplate.image_height,
                Instruments.LENS,
            )
        else:
            pass

        if TESTING:
            Path(filepath).touch()
        else:
            capture_new_image(save=True, num_images=1, file_name=filepath)
        logger.debug("Image of well %s captured", instructions.well_id)
        # upload image to OBS
        # logger.info("Uploading image of well %s to OBS", instructions.well_id)
        instructions.results.image_files.append(filepath)
    except Exception as e:
        logger.exception(
            "Failed to image well %s. Error %s occured", instructions.well_id, e
        )
        # raise ImageCaputreFailure(instructions.well_id) from e
        # don't raise anything and continue with the experiment. The image is not critical to the experiment
    finally:
        # move camera to safe position
        if well_id != "test":
            logger.info("Moving camera to safe position")
            toolkit.mill.move_to_safe_position()  # move to safe height above target well


class OCPFailure(Exception):
    """Raised when OCP fails"""

    def __init__(self, stage):
        self.stage = stage
        self.message = f"OCP failed before {stage}"
        super().__init__(self.message)


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)


class ImageCaputreFailure(Exception):
    """Raised when image capture fails"""

    def __init__(self, well_id):
        self.well_id = well_id
        self.message = f"Image capture failed for well {well_id}"
        super().__init__(self.message)


class DepositionFailure(Exception):
    """Raised when deposition fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = (
            f"Deposition failed for experiment {experiment_id} well {well_id}"
        )
        super().__init__(self.message)


class CAFailure(Exception):
    """Raised when CA fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = f"CA failed for experiment {experiment_id} well {well_id}"
        super().__init__(self.message)


class CVFailure(Exception):
    """Raised when CV fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = f"CV failed for experiment {experiment_id} well {well_id}"
        super().__init__(self.message)


if __name__ == "__main__":
    pass
