"""For testing the contamination from the pipette tip"""
# Standard imports
from typing import Sequence

# Non-standard imports
from instrument_toolkit import Toolkit
from e_panda import (
    forward_pipette_v2,
    solution_selector,
    cyclic_volt,
    waste_selector,
)
from experiment_class import ExperimentBase, ExperimentStatus
from vials import StockVial, WasteVial

from correction_factors import correction_factor


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
    # Start of experiment

    # Apply correction factor to the programmed volumes
    print("Applying correction factor to the programmed volumes")
    instructions.solutions_corrected["electrolyte"] = correction_factor(
        instructions.solutions["electrolyte"],
        solution_selector(
            stock_vials, "electrolyte", instructions.solutions["electrolyte"]
        ).viscosity_cp,
    )

    instructions.solutions_corrected["rinse0"] = correction_factor(
        instructions.solutions["rinse0"],
        solution_selector(
            stock_vials, "rinse0", instructions.solutions["rinse0"]
        ).viscosity_cp,
    )

    instructions.solutions_corrected["5mm_fecn6"] = correction_factor(
        instructions.solutions["5mm_fecn6"],
        solution_selector(
            stock_vials, "5mm_fecn6", instructions.solutions["5mm_fecn6"]
        ).viscosity_cp,
    )

    print("Corrected volumes: ", instructions.solutions_corrected)

    if instructions.solutions["5mm_fecn6"] > 0:
        # Pipette 120ul of fecn6 solution into waste to dirty the pipette tip
        print("Pipetting 120ul of fecn6 solution into waste to dirty the pipette tip")
        forward_pipette_v2(
            volume=instructions.solutions["5mm_fecn6"],
            from_vessel=solution_selector(
                stock_vials,
                "5mm_fecn6",
                instructions.solutions["5mm_fecn6"],
            ),
            to_vessel=waste_selector(
                waste_vials, "waste", instructions.solutions["5mm_fecn6"]
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

        # Flush the pipette tip x3 with electrolyte rinse
        print("2. Flushing the pipette tip x3 with electrolyte rinse")
        for _ in range(3):
            forward_pipette_v2(
                volume=instructions.solutions["rinse0"],
                from_vessel=solution_selector(
                    stock_vials, "rinse0", instructions.solutions["rinse0"]
                ),
                to_vessel=waste_selector(
                    waste_vials, "waste", instructions.solutions["rinse0"]
                ),
                pump=toolkit.pump,
                mill=toolkit.mill,
                pumping_rate=instructions.pumping_rate,
            )

        # Pipette 120ul of electrolyte solution into well
        print("3. Pipetting 120ul of electrolyte into well")
        forward_pipette_v2(
            volume=instructions.solutions["electrolyte"],  # 120
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
        print("1. Pipetting 120ul of electrolyte into well")
        forward_pipette_v2(
            volume=instructions.solutions["electrolyte"],  # 120
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
    print("4. Performing CV")
    cyclic_volt(
        char_instructions=instructions,
        char_results=instructions.results,
        mill=toolkit.mill,
        wellplate=toolkit.wellplate,
    )

    # Rinse the electrode with electrode rinse
    print("5. Rinsing electrode")
    toolkit.mill.rinse_electrode()

    # Clear the well
    print("6. Clearing well")
    forward_pipette_v2(
        volume=instructions.solutions["electrolyte"],
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials, "waste", instructions.solutions["electrolyte"]
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # End of experiment
    instructions.status = ExperimentStatus.COMPLETE
