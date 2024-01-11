"""For testing the contamination from the pipette tip"""
# Standard imports
import json
from typing import Sequence

# Non-standard imports
from controller import Toolkit
from e_panda import (
    forward_pipette_v2,
    solution_selector,
    characterization,
    waste_selector,
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
    if instructions.solutions['5mm_fecn3'] > 0:
        # Pipette 120ul of fecn3 solution into waste to dirty the pipette tip
        forward_pipette_v2(
            volume=instructions.solutions['5mm_fecn3'],
            from_vessel=solution_selector(
                stock_vials,
                '5mm_fecn3',
                instructions.solutions['5mm_fecn3'],
            ),
            to_vessel=waste_selector(
                waste_vials, "waste", instructions.solutions['5mm_fecn3']
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

        # Flush the pipette tip x3 with electrolyte rinse
        for _ in range(3):
            forward_pipette_v2(
                volume=instructions.solutions['rinse0'],
                from_vessel=solution_selector(
                    stock_vials, "rinse0", instructions.solutions['rinse0']
                ),
                to_vessel=waste_selector(
                    waste_vials, "waste", instructions.solutions['rinse0']
                ),
                pump=toolkit.pump,
                mill=toolkit.mill,
                pumping_rate=instructions.pumping_rate,
            )

        # Pipette 120ul of electrolyte solution into well
        forward_pipette_v2(
            volume=instructions.solutions["electrolyte"], #120
            from_vessel=solution_selector(
                stock_vials,
                "electrolyte",
                instructions.solutions["electrolyte"],
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    else:
        # Pipette 120ul of electrolyte solution into well
        forward_pipette_v2(
            volume=instructions.solutions["electrolyte"], #120
            from_vessel=solution_selector(
                stock_vials,
                "electrolyte",
                instructions.solutions["electrolyte"],
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
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
