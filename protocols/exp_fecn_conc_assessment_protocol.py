"""
FeCn concentration assessment
Author: Harley Quinn
Date: 2024-05-28
Description:
    Protocol for testing two different concentrations of ferrocyanide solution
    using cyclic voltammetry

Reviewer: Gregory Robben
Date: 2024-06-01
    
"""

# Standard imports
from typing import Sequence

# Non-standard imports
from epanda_lib.controller import Toolkit
from epanda_lib.e_panda import (
    forward_pipette_v2,
    solution_selector,
    cyclic_volt,
    waste_selector,
    image_well,
    flush_v2,
)
from epanda_lib.experiment_class import ExperimentBase, ExperimentStatus
from epanda_lib.vials import StockVial, WasteVial
from epanda_lib.correction_factors import correction_factor
from epanda_lib.mill_control import Instruments


def main(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """Runs the FeCn concentration assessment experiment."""
    fecn_conc_experiment(
        instructions=instructions,
        toolkit=toolkit,
        stock_vials=stock_vials,
        waste_vials=waste_vials,
    )


def fecn_conc_experiment(
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
    solution_name = "5mm_fecn6"
    current_well = toolkit.wellplate.wells[instructions.well_id]
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before type 1 experiment")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing %s into well: %s", solution_name, instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected[solution_name],
        from_vessel=solution_selector(
            stock_vials,
            solution_name,
            instructions.solutions_corrected[solution_name],
        ),
        to_vessel=current_well,
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
        # Set the feed rate to 100 to avoid splashing
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
        cyclic_volt(instructions, file_tag="type_1")
    finally:
        toolkit.global_logger.info("3. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(rinses=3)

    # Clear the well
    toolkit.global_logger.info("4. Clearing well contents into waste")
    instructions.set_status(ExperimentStatus.CLEARING)

    forward_pipette_v2(
        volume=current_well.volume,
        from_vessel=current_well,
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            current_well.volume,
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
            to_vessel=current_well,
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=current_well,
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                correction_factor(120),
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
        )

    toolkit.global_logger.info("Experiment %d complete\n\n", instructions.experiment_id)
