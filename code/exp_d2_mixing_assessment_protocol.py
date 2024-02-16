"""
Protocol for testing the mixing of the ferrocyanide solution cyclic voltammetry
"""

from typing import Sequence
from experiment_class import ExperimentBase, ExperimentStatus
from controller import Toolkit
from vials import StockVial, WasteVial
from e_panda import (
    forward_pipette_v2,
    characterization,
    solution_selector,
    waste_selector,
    flush_v2,
    image_well,
)
from correction_factors import correction_factor
from mill_control import Instruments


def mixing_assessment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the mixing in our system.
    There are three types of experiments:

    Type 1: No mixing
        1. Pipette 120ul of 5mm_fecn6 into the well
        2. Perform CV
        3. Rinse the electrode
        4. Clear the well
        5. Flush the pipette tip

    Type 2: Mixing of 10mm_fecn6 into electrolyte
        1. Pipette 60ul of 10mm_fecn6 into the well
        2. Pipette 60ul of electrolyte into the well
        3. Perform CV
        4. Rinse the electrode
        5. Clear the well
        6. Flush the pipette tip

    Type 3: Mixing of electrolyte into 10mm_fecn6
        1. Pipette 60ul of electrolyte into the well
        2. Pipette 60ul of 10mm_fecn6 into the well
        3. Perform CV
        4. Rinse the electrode
        5. Clear the well
        6. Flush the pipette tip

    This method will run combinations of the three types of experiments in series in the same well
    to test the mixing of the solutions.

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        toolkit (Toolkit object): The toolkit object which contains the pump, mill, and wellplate
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None - all arguments are passed by reference or are unchanged

    """
    # Check that all requested solutions are available
    # although we already checked before running the experiment we want to check again
    # that all requested solutions are found
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

    experiment_type_pattern = {
        0: 1,
        1: 2,
        2: 3,
        3: 1,
        4: 3,
        5: 2,
        6: 1,
        7: 2,
        8: 3,
        9: 1,
    }
    for i in range(10):
        # Repeat the instruction set for each type of experiment
        if experiment_type_pattern[i] == 1:
            type_1_experiment(
                instructions,
                toolkit,
                stock_vials,
                waste_vials,
            )

        elif experiment_type_pattern[i] == 2:
            type_2_experiment(
                instructions,
                toolkit,
                stock_vials,
                waste_vials,
            )

        elif experiment_type_pattern[i] == 3:
            type_3_experiment(
                instructions,
                toolkit,
                stock_vials,
                waste_vials,
            )
        if i == 0:
            user_choice = input(
                "Do you want to continue with the next experiment? (y/n): "
            )
            if user_choice.lower() == "n":
                break
        else:
            continue


def type_1_experiment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Type 1: No mixing
        1. Pipette 120ul of 5mm_fecn6 into the well
        2. Perform CV
        3. Rinse the electrode
        4. Clear the well
        5. Flush the pipette tip
        6. Rinse the well 4x with rinse
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before type 1 experiment")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing 5mm_fecn6 into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected["5mm_fecn6"],
        from_vessel=solution_selector(
            stock_vials,
            "5mm_fecn6",
            instructions.solutions_corrected["5mm_fecn6"],
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

        toolkit.global_logger.info("2. Performing CV")
        characterization(instructions, file_tag="type_1")
    finally:
        toolkit.global_logger.info("3. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("4. Clearing well contents into waste")
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

    toolkit.global_logger.info("5. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=1,
    )

    toolkit.global_logger.info("6. Rinsing the well 4x with rinse")
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
            pumping_rate=instructions.pumping_rate,
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

    toolkit.global_logger.info("Experiment complete\n\n")


def type_2_experiment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Type 2: Mixing of 10mm_fecn6 into electrolyte
        1. Pipette 60ul of 10mm_fecn6 into the well
        2. Pipette 60ul of electrolyte into the well
        3. Move Electrode to well
        4. Perform CV
        5. Rinse the electrode
        6. Clear the well
        7. Flush the pipette tip
        8. Rinse the well 4x with rinse
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before type 2 experiment")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing 10mm_fecn6 into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=correction_factor(60),
        from_vessel=solution_selector(
            stock_vials,
            "10mm_fecn6",
            correction_factor(60),
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )
    toolkit.global_logger.info(
        "2. Depositing electrolyte into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=correction_factor(60),
        from_vessel=solution_selector(
            stock_vials,
            "electrolyte",
            correction_factor(60),
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("3. Moving electrode to well: %s", instructions.well_id)
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

        toolkit.global_logger.info("4. Performing CV")
        characterization(instructions, file_tag="type_2")
    finally:
        toolkit.global_logger.info("5. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("6. Clearing well contents into waste")
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

    toolkit.global_logger.info("7. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=1,
    )

    toolkit.global_logger.info("8. Rinsing the well 4x with rinse")
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
            pumping_rate=instructions.pumping_rate,
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
    toolkit.global_logger.info("Experiment complete\n\n")


def type_3_experiment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Type 3: Mixing of electrolyte into 10mm_fecn6
        1. Pipette 60ul of electrolyte into the well
        2. Pipette 60ul of 10mm_fecn6 into the well
        3. Move Electrode to well
        4. Perform CV
        5. Rinse the electrode
        6. Clear the well
        7. Flush the pipette tip
        8. Rinse the well 4x with rinse
    """

    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before type 3 experiment")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing electrolyte into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=correction_factor(60),
        from_vessel=solution_selector(
            stock_vials,
            "electrolyte",
            correction_factor(60),
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )
    toolkit.global_logger.info(
        "2. Depositing 10mm_fecn6 into well: %s", instructions.well_id
    )
    forward_pipette_v2(
        volume=correction_factor(60),
        from_vessel=solution_selector(
            stock_vials,
            "10mm_fecn6",
            correction_factor(60),
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("3. Moving electrode to well: %s", instructions.well_id)
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

        toolkit.global_logger.info("4. Performing CV")
        characterization(instructions, file_tag="type_3")
    finally:
        toolkit.global_logger.info("5. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("6. Clearing well contents into waste")
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

    toolkit.global_logger.info("7. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=1,
    )
    toolkit.global_logger.info("6. Rinsing the well 4x with rinse")
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
            pumping_rate=instructions.pumping_rate,
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
    toolkit.global_logger.info("Experiment complete\n\n")
