"""
Protocol for testing the repeatability of the ferrocyanide solution cyclic voltammetry
"""
from typing import Sequence
from experiment_class import ExperimentBase, ExperimentStatus
from controller import Toolkit
from vials import StockVial, WasteVial
from e_panda import (
    forward_pipette_v2,
    cyclic_volt,
    solution_selector,
    waste_selector,
    flush_v2,
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
                solution,  # The solution name
                instructions.solutions[solution],  # The volume of the solution
            ).viscosity_cp,
        )

    if instructions.process_type == 1:
        type_1_experiment(instructions, toolkit, stock_vials, waste_vials)
    elif instructions.process_type == 2:
        type_2_experiment(instructions, toolkit, stock_vials, waste_vials)
    elif instructions.process_type == 3:
        type_3_experiment(instructions, toolkit, stock_vials, waste_vials)
    else:
        raise ValueError("Invalid process type")


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
    """
    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    print("1. Depositing 5mm_fecn6 into well: ", instructions.well_id)
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
    print("2. Moving electrode to well:", instructions.well_id)
    try:
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        print("2. Performing CV")
        cyclic_volt(
            instructions, instructions.results, toolkit.mill, toolkit.wellplate
        )
    finally:
        print("3. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    print("4. Clearing well contents into waste")
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

    print("5. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse0",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=3,
    )
    print("Experiment complete\n\n")


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
    """
    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    print("1. Depositing 10mm_fecn6 into well: ", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["10mm_fecn6"],
        from_vessel=solution_selector(
            stock_vials,
            "10mm_fecn6",
            instructions.solutions_corrected["10mm_fecn6"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )
    print("2. Depositing electrolyte into well: ", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["electrolyte"],
        from_vessel=solution_selector(
            stock_vials,
            "electrolyte",
            instructions.solutions_corrected["electrolyte"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    print("3. Moving electrode to well:", instructions.well_id)
    try:
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        print("4. Performing CV")
        cyclic_volt(
            instructions, instructions.results, toolkit.mill, toolkit.wellplate
        )
    finally:
        print("5. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    print("6. Clearing well contents into waste")
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

    print("7. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse0",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=3,
    )

    print("Experiment complete\n\n")


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
    """
    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    print("1. Depositing electrolyte into well: ", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["electrolyte"],
        from_vessel=solution_selector(
            stock_vials,
            "electrolyte",
            instructions.solutions_corrected["electrolyte"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )
    print("2. Depositing 10mm_fecn6 into well: ", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["10mm_fecn6"],
        from_vessel=solution_selector(
            stock_vials,
            "10mm_fecn6",
            instructions.solutions_corrected["10mm_fecn6"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    print("3. Moving electrode to well:", instructions.well_id)
    try:
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        print("4. Performing CV")
        cyclic_volt(
            instructions, instructions.results, toolkit.mill, toolkit.wellplate
        )
    finally:
        print("5. Rinsing electrode")
        instructions.set_status(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    print("6. Clearing well contents into waste")
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

    print("7. Flushing the pipette tip")
    instructions.set_status(ExperimentStatus.FLUSHING)
    flush_v2(
        waste_vials=waste_vials,
        stock_vials=stock_vials,
        flush_solution_name="rinse0",
        mill=toolkit.mill,
        pump=toolkit.pump,
        flush_count=3,
    )

    print("Experiment complete\n\n")
