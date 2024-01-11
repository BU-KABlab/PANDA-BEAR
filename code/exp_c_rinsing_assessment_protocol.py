"""For testing the contamination from the pipette tip"""
# Standard imports
import json
from json import tool
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


def rinsing_assessment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the conamination coming from the electrode
    1. Pipette 120 µl of fecn3 into well
    2. Perform CV in the well
    3. Rinse the electrode in electrode bath
    4. Clear the well contents into waste
    5. Rinse the pipette tip with electrolyte rinse (rine0) x3
    6. Pipette 120 µl of electrolyte into well
    7. Perform CV in the well
    Repeat steps 3-7 for a total of 11 rinses and CV after rinsing

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
    print("1. Pipetting 120ul of 5mm_fecn3 into well: ", instructions.well_id)
    # Pipette 120ul of fecn3 solution into well
    forward_pipette_v2(
        volume=instructions.solutions['5mm_fecn3'],
        from_vessel=solution_selector(
            stock_vials,
            '5mm_fecn3',
            instructions.solutions['5mm_fecn3'],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )


    # Perform CV
    print("2. Performing CV")
    characterization(
        char_instructions=instructions,
        char_results=instructions.results,
        mill=toolkit.mill,
        wellplate=toolkit.wellplate,
    )
    for i in range(11):
        # Rinse the electrode with electrode rinse
        print(f"3.{i} Rinsing electrode")
        toolkit.mill.rinse_electrode()

        # Clear the well contents into waste
        print(f"4.{i} Clearing well contents into waste")
        forward_pipette_v2(
            volume=instructions.solutions['5mm_fecn3'],
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                'waste',
                instructions.solutions['5mm_fecn3'],
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

        # Flush the pipette tip x3 with electrolyte rinse
        print(f"5.{i} Flushing pipette tip with electrolyte rinse")
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
        print(f"6.{i} Pipetting 120ul of electrolyte into well: ", instructions.well_id)
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
        print(f"7.{i} Performing CV")
        characterization(
            char_instructions=instructions,
            char_results=instructions.results,
            mill=toolkit.mill,
            wellplate=toolkit.wellplate,
        )

    # End of experiment
    instructions.status = ExperimentStatus.COMPLETE
