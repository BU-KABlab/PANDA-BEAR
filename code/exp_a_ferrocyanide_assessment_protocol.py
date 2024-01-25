"""
Protocol for testing the repeatability of the ferrocyanide solution cyclovoltammetry
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
    image_well,
)
from correction_factors import correction_factor
from mill_control import Instruments

def ferrocyanide_repeatability(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the repeatability of the ferrocyanide solution cyclovoltammetry
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Read the scale
            d. Deposit into well
            e. Blow out
            f. Read the scale
            g. Perform CV
            h. Clear the well

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
    print("Applying correction factor to the programmed volumes")
    for solution in instructions.solutions:
        instructions.solutions_corrected[solution] = correction_factor(
            instructions.solutions[solution],
            solution_selector(
                stock_vials,
                solution, # The solution name
                instructions.solutions[solution] # The volume of the solution
            ).viscosity_cp,
        )

    ## Image the new well
    image_well(
        wellplate=toolkit.wellplate,
        instructions=instructions.well_id,
        toolkit=toolkit,
        step_description="new"
    )

    instructions.status = ExperimentStatus.DEPOSITING
    ## Deposit the experiment solution into the well
    forward_pipette_v2(
        volume=instructions.solutions_corrected['5mm_fecn6'],
        from_vessel=solution_selector(
            stock_vials,
            '5mm_fecn6',
            instructions.solutions_corrected['5mm_fecn6'],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, 'x'),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, 'y'),
        z_coord=toolkit.wellplate.echem_height,
        instrument=Instruments.ELECTRODE,
    )
    # Initial fluid handeling is done now we can perform the CV
    characterization(instructions,instructions.results, toolkit.mill, toolkit.wellplate)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    instructions.status = ExperimentStatus.CLEARING
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

    ## Image the cleared well
    image_well(
        wellplate=toolkit.wellplate,
        instructions=instructions.well_id,
        toolkit=toolkit,
        step_description="cleared"
    )
