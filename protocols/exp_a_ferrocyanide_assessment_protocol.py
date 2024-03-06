"""
Protocol for testing the repeatability of the ferrocyanide solution cyclic voltammetry
"""

from typing import Sequence
from experiment_class import EchemExperimentBase, ExperimentStatus
from controller import Toolkit
from vials import StockVial, WasteVial
from e_panda import (
    forward_pipette_v2,
    cyclic_volt,
    solution_selector,
    waste_selector,
    image_well,
)
from correction_factors import correction_factor
from mill_control import Instruments


def ferrocyanide_repeatability(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the repeatability of the ferrocyanide solution cyclic voltammetry

    Steps:
    0. Image the well
    1. Deposit the experiment solution into the well
    2. Move the electrode to the well
    3. Perform the cyclic voltammetry
    4. Clear the well contents into waste


    Args:
        instructions (Experiment object): The experiment instructions
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
    logger = toolkit.global_logger
    print("Applying correction factor to the programmed volumes")
    logger.info("Applying correction factor to the programmed volumes")
    for solution in instructions.solutions:
        instructions.solutions_corrected[solution] = correction_factor(
            instructions.solutions[solution],
            solution_selector(
                stock_vials,
                solution,  # The solution name
                instructions.solutions[solution],  # The volume of the solution
            ).viscosity_cp,
        )
    logger.info("Correction factor applied to the programmed volumes")
    logger.debug(f"Corrected volumes: {instructions.solutions_corrected}")
    logger.debug(f"Original volumes: {instructions.solutions}")

    print("0. Imaging the well")
    logger.info("Imaging the well")
    instructions.set_status(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "before_repeat_experiment")

    instructions.set_status(ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    print("1. Depositing solutions into well: ", instructions.well_id)
    logger.info("Depositing solutions into well: %s", instructions.well_id)
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
    print("2. Moving electrode to well: ", instructions.well_id)
    logger.info("Moving electrode to well: %s", instructions.well_id)
    try:
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        print("3. Performing CV")
        logger.info("Performing CV")
        logger.debug("%s", instructions.print_cv_parameters())
        cyclic_volt(instructions)
    finally:
        instructions.set_status(ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    print("4. Clearing well contents into waste")
    logger.info("Clearing well contents into waste")
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
    print("Experiment complete\n\n")
    logger.info(
        "Experiment %d.%d.%d complete",
        instructions.project_id,
        instructions.project_campaign_id,
        instructions.id,
    )
