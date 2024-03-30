"""
Notes:
-   All depositions are CVs, using the same settings EXCEPT number of cycles.
-   All characterizations are CVs, using different settings than the depositions, 
    but the same settings for all characterizations.
-   The characterization solutions are pipetted in manually right before each 
    experiment because of how long the characterization CVs will take 
    (we are minimizing the evaporation of the solution).
"""
# Standard imports
from typing import Sequence

from epanda_lib.controller import Toolkit
from epanda_lib.correction_factors import correction_factor
from epanda_lib.e_panda import (cyclic_volt, forward_pipette_v2, image_well,
                                solution_selector, waste_selector)
from epanda_lib.experiment_class import EchemExperimentBase, ExperimentStatus
from epanda_lib.mill_control import Instruments
from epanda_lib.vials import StockVial, WasteVial


def edot_bleaching_part_1(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Experiment part 1 - Deposition using CV
        0. Apply correction factor to the programmed volumes
        1. Take before image
        2. Pipette 120 µL of EDOT solution into well
        3. Run cyclic
            Cvvi = 0
            CVap1 = 2
            CVap2 = 0.5
            CVvf = 0.5
            CVsr1 = 0.05
            Cvcycle = #  <-- different for each experiment
        4. Move EDOT solution from well to waste
        5. Rinse pipette tip 3x with electrolyte rinse
        6. Rinse well 4x with electrolyte well rinse
        7. Take after image
         (well should be clear of solution)

    """
    # Apply correction factor to the programmed volumes
    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 1 started"
    )

    print("0. Applying correction factor to the programmed volumes")
    for solution in instructions.solutions:
        instructions.solutions_corrected[solution] = correction_factor(
            instructions.solutions[solution],
            solution_selector(
                stock_vials,
                solution,  # The solution name
                instructions.solutions[solution],  # The volume of the solution
            ).viscosity_cp,
        )

    print(instructions.solutions_corrected)

    print("1. Taking before image")
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="before",
    )

    # Pipette 120ul of edot solution into well
    print(
        f"2. Pipetting  {instructions.solutions_corrected['edot']}ul of edot into well: {instructions.well_id}"
    )
    instructions.set_status_and_save(ExperimentStatus.DEPOSITING)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["edot"],
        from_vessel=solution_selector(
            stock_vials,
            "edot",
            instructions.solutions_corrected["edot"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Move the electrode to the well
    print("Moving electrode to well")
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["x"],
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["y"],
        z_coord=toolkit.wellplate.echem_height,
        instrument=Instruments.ELECTRODE,
    )
    # Perform CV
    print("3. Performing CV with the following parameters:")
    print("\tCvvi = ", instructions.cv_initial_voltage)
    print("\tCVap1 = ", instructions.cv_first_anodic_peak)
    print("\tCVap2 = ", instructions.cv_second_anodic_peak)
    print("\tCVvf = ", instructions.cv_final_voltage)
    print("\tCVsr1 = ", instructions.cv_scan_rate_cycle_1)
    print("\tCvcycle = ", instructions.cv_cycle_count)
    try:
        cyclic_volt(
            char_instructions=instructions,
            file_tag="part_1",
        )
    except Exception as e:
        print("Error in characterization")
        print(e)
        print("Continuing with the rest of the experiment")

    finally:
        instructions.set_status_and_save(ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode()

    # Clear the well contents into waste
    print("3. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["edot"],
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            instructions.solutions_corrected["edot"],
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Flush the pipette tip x3 with electrolyte rinse
    print("4. Flushing pipette tip with electrolyte rinse")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    for _ in range(3):
        forward_pipette_v2(
            volume=instructions.solutions_corrected["electrolyte"],
            from_vessel=solution_selector(
                stock_vials,
                "electrolyte",
                instructions.solutions_corrected["electrolyte"],
            ),
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                instructions.solutions_corrected["electrolyte"],
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    # Rinse the well 4x with electrolyte rinse
    print("5. Rinsing well 4x with electrolyte well rinse")
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for _ in range(4):
        forward_pipette_v2(
            volume=instructions.solutions_corrected["rinse0"],
            from_vessel=solution_selector(
                stock_vials,
                "rinse0",
                instructions.solutions_corrected["rinse0"],
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

        forward_pipette_v2(
            volume=instructions.solutions_corrected["rinse0"],
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                "waste",
                instructions.solutions_corrected["rinse0"],
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    print("Taking after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="after deposition",
    )

    toolkit.mill.rest_electrode()
    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 1 complete"
    )
    print("*" * 80, end="\n\n")


def edot_bleaching_part_2(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Experiment part 2 - Characterization
        1. Pipette the LiClO4 solution into the well
        2. Move the electrode to the well
        3. Run cyclic
            Cvvi = 0
            CVap1 = -1.6 (this is intentionally negative)
            CVap2 = 0.4
            CVvf = -1.6
            CVsr1 = 0.025
            Cvcycle = 3
        5. Image the well

    """
    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 2 started"
    )

    print(
        "1. Pipetting 120µL of 0.1M LiClO4 in water into well. Press enter to confirm"
    )
    instructions.set_status_and_save(ExperimentStatus.DEPOSITING)
    forward_pipette_v2(
        volume=instructions.solutions_corrected["licl04"],
        from_vessel=solution_selector(
            stock_vials,
            "licl04",
            instructions.solutions_corrected["licl04"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Move the electrode to the well
    print("2. Moving electrode to well")
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["x"],
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["y"],
        z_coord=toolkit.wellplate.echem_height,
        instrument=Instruments.ELECTRODE,
    )
    # Run cyclic
    print("3. Running CV with the following parameters:")
    print("\tCvvi = ", instructions.cv_initial_voltage)
    print("\tCVap1 = ", instructions.cv_first_anodic_peak)
    print("\tCVap2 = ", instructions.cv_second_anodic_peak)
    print("\tCVvf = ", instructions.cv_final_voltage)
    print("\tCVsr1 = ", instructions.cv_scan_rate_cycle_1)
    print("\tCvcycle = ", instructions.cv_cycle_count)

    cyclic_volt(
        char_instructions=instructions,
        file_tag="part_2",
    )

    print("4. Imaging well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="after characterization",
    )

    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 2 complete"
    )
    print("*" * 80, end="\n\n")
