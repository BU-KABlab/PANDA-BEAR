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
    NoAvailableSolution,
)


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
    available_solutions = [
        vial.name
        for vial in stock_vials
        if vial.name not in ["rinse0", "rinse1", "rinse2"]
    ]

    instruction_solutions = list(instructions.solutions.keys())

    # Check that all requested solutions are available
    # although we already checked before running the experiment we want to check again
    # that all requested solutions are found

    ## Deposit the experiment solution into the well
    for solution_name in instruction_solutions:
        if solution_name not in available_solutions:
            raise NoAvailableSolution(
                "Solution {} is not available".format(solution_name)
            )
        forward_pipette_v2(
            volume=instructions.solutions[solution_name],
            from_vessel=solution_selector(
                stock_vials,
                solution_name,
                instructions.solutions[solution_name],
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    # Initial fluid handeling is done now we can perform the CV
    characterization(instructions,instructions.results, toolkit.mill, toolkit.wellplate)
    # Clear the well
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
    instructions.status = ExperimentStatus.COMPLETE
