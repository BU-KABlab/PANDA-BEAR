"""For testing the contamination from the pipette tip"""
# Standard imports
import json
from typing import Sequence

# Non-standard imports
from controller import Toolkit
from e_panda import (
    NoAvailableSolution,
    forward_pipette_v2,
    solution_selector,
    characterization,
)
from experiment_class import ExperimentBase, ExperimentStatus
from vials import StockVial, WasteVial


def contamination_assessment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the conamination coming from the pipette tip
    1. Deposit solutions into well
        for each solution:
            a. Pipette 120ul of solution into waste
            b. Flush the pipette tip x3 with electrolyte rinse
            c. Pipette 120ul of solution into well
            d. Perform CV
            e. Rinse the electrode with electrode rinse

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        toolkit (Toolkit object): The toolkit object which contains the pump, mill, and wellplate
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None - all arguments are passed by reference or are unchanged

    """

    toolkit.global_logger.info(
        "Pipetting %s ul of %s into %s...",
        instructions.solutions['5mm_fecn3'],
        '5mm_fecn3',
        'waste',
    )

    # Pipette 120ul of fecn3 solution into waste to dirty the pipette tip
    forward_pipette_v2(
        volume=instructions.solutions['5mm_fecn3'],
        from_vessel=solution_selector(
            stock_vials,
            '5mm_fecn3',
            instructions.solutions['5mm_fecn3'],
        ),
        to_vessel=solution_selector(
            stock_vials, "waste", instructions.solutions['5mm_fecn3']
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Flush the pipette tip x3 with electrolyte rinse
    for _ in range(3):
        forward_pipette_v2(
            volume=instructions.solutions['electrolye_rinse'],
            from_vessel=solution_selector(
                stock_vials, "rinse0", instructions.solutions['electrolye_rinse']
            ),
            to_vessel=solution_selector(
                stock_vials, "waste", instructions.solutions['electrolye_rinse']
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    # Pipette 120ul of electrolye solution into well
    forward_pipette_v2(
        volume=instructions.solutions["electrolye"], #120
        from_vessel=solution_selector(
            stock_vials,
            "electrolye",
            instructions.solutions["electrolye"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    toolkit.global_logger.info(
        "Pipetted %s into well: %s",
        json.dumps(instructions.solutions),
        instructions.well_id,
    )

    # Perform CV
    characterization(
        char_instructions=instructions,
        char_results=instructions.results,
        mill=toolkit.mill,
        wellplate=toolkit.wellplate,
    )

    # Rinse the electrode with electrode rinse
    toolkit.mill.rinse_electrode()

    # End of experiment
    instructions.status = ExperimentStatus.COMPLETE
