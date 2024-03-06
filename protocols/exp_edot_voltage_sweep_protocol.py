"""
Notes:
-   All depositions are CAs
-   All characterizations are CAs
"""

# Standard imports
from typing import Sequence

# Non-standard imports
from epanda_lib.instrument_toolkit import Toolkit
from epanda_lib.correction_factors import correction_factor
from epanda_lib.e_panda import (chrono_amp, flush_v2, forward_pipette_v2,
                                image_well, solution_selector, waste_selector)
from epanda_lib.experiment_class import EchemExperimentBase, ExperimentStatus
from epanda_lib.mill_control import Instruments
from epanda_lib.vials import StockVial, WasteVial


def pedotinitial_screening(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    The initial screening of the edot solution
    Per experiment:
    0. Apply correction factor to the programmed volumes
    1. pedotdeposition
    2. pedotbleaching
    3. pedotcoloring

    """
    # Apply correction factor to the programmed volumes
    toolkit.global_logger.info("Applying correction factor to the programmed volumes")
    for solution in instructions.solutions:
        instructions.solutions_corrected[solution] = correction_factor(
            instructions.solutions[solution],
            solution_selector(
                stock_vials,
                solution,  # The solution name
                instructions.solutions[solution],  # The volume of the solution
            ).viscosity_cp,
        )

    # Run the experiment based on its experiment type
    if instructions.process_type == 1:
        pedotdeposition(
            instructions=instructions,
            toolkit=toolkit,
            stock_vials=stock_vials,
            waste_vials=waste_vials,
        )
    elif instructions.process_type == 2:
        pedotbleaching(
            instructions=instructions,
            toolkit=toolkit,
            stock_vials=stock_vials,
            waste_vials=waste_vials,
        )

    elif instructions.process_type == 3:
        pedotcoloring(
            instructions=instructions,
            toolkit=toolkit,
            stock_vials=stock_vials,
            waste_vials=waste_vials,
        )


def pedotdeposition(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    0. Imaging the well
    1. Depositing EDOT into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Rinsing the well 4x with rinse
    8. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before_deposition")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info("1. Depositing EDOT into well: %s", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["edot"],
        from_vessel=solution_selector(
            stock_vials,
            "edot",
            instructions.solutions_corrected["edot"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate to 1000 to avoid splashing
        toolkit.mill.set_feed_rate(100)
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate back to 2000
        toolkit.mill.set_feed_rate(2000)

        toolkit.global_logger.info("3. Performing CA deposition")
        chrono_amp(instructions, file_tag="part_1")
    finally:
        toolkit.global_logger.info("4. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=1,
    )

    toolkit.global_logger.info("7. Rinsing the well 4x with rinse")
    instructions.set_status(ExperimentStatus.RINSING)
    for _ in range(4):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=solution_selector(
                stock_vials,
                "rinse",
                correction_factor(120),
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
            volume=correction_factor(120),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                correction_factor(120),
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
        )

    toolkit.global_logger.info("8. Take after image")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="after_deposition",
    )
    toolkit.global_logger.info("PEDOT deposition complete\n\n")


def pedotbleaching(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    0. Imaging the well
    1. Depositing liclo4 into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "bleaching_before_CA")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info("1. Depositing EDOT into well: %s", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["liclo4"],
        from_vessel=solution_selector(
            stock_vials,
            "liclo4",
            instructions.solutions_corrected["liclo4"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate to 1000 to avoid splashing
        toolkit.mill.set_feed_rate(100)
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate back to 2000
        toolkit.mill.set_feed_rate(2000)

        toolkit.global_logger.info("3. Performing CA")
        chrono_amp(instructions, file_tag="bleaching")
    finally:
        toolkit.global_logger.info("4. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=1,
    )

    toolkit.global_logger.info("7. Take after image")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="bleaching_after_CA",
    )

    toolkit.global_logger.info("PEDOT bleaching complete\n\n")


def pedotcoloring(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    0. Imaging the well
    1. Depositing liclo4 into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Take image of well
    8. Rinsing the well 4x with rinse
    9. Take end image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "coloring_before_CA")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected["liclo4"],
        from_vessel=solution_selector(
            stock_vials,
            "liclo4",
            instructions.solutions_corrected["liclo4"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate to 1000 to avoid splashing
        toolkit.mill.set_feed_rate(100)
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate back to 2000
        toolkit.mill.set_feed_rate(2000)

        toolkit.global_logger.info("3. Performing CA")
        chrono_amp(instructions, file_tag="coloring")
    finally:
        toolkit.global_logger.info("4. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=3,
    )

    toolkit.global_logger.info("7. Take image of well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="coloring_after_CA",
    )
    toolkit.global_logger.info("8. Rinsing the well 4x with rinse")
    instructions.set_status(ExperimentStatus.RINSING)
    for _ in range(4):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=solution_selector(
                stock_vials,
                "rinse",
                correction_factor(120),
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=toolkit.pump.max_pump_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                correction_factor(120),
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
        )

    toolkit.global_logger.info("9. Take end image")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="coloring_after_rinse",
    )

    toolkit.global_logger.info("PEDOT coloring complete\n\n")