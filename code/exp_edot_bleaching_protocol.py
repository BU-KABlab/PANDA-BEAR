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

# Non-standard imports
from controller import Toolkit
from e_panda import (
    forward_pipette_v2,
    solution_selector,
    characterization,
    waste_selector,
    image_well,
)
from experiment_class import EchemExperimentBase, ExperimentStatus
from vials import StockVial, WasteVial
from correction_factors import correction_factor
from mill_control import Instruments


def edot_bleaching_part_1(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Experiment part 1 - Deposition using CV
         1. Pipette 120 µL of EDOT solution into well B2
         2. Run cyclic
             Cvvi = 0
             CVap1 = 2
             CVap2 = 0.5
             CVvf = 0.5
             CVsr1 = 0.05
             Cvcycle = #  <-- different for each experiment
         3. Move EDOT solution from well B2 to waste
         4. Rinse pipette tip 3x with electrolyte rinse
         5. Rinse well 4x with electrolyte well rinse
         (well should be clear of solution)

    """
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

    print(instructions.solutions_corrected)

    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 1 started"
    )
    print("Deposition using CV")
    # Pipette 120ul of edot solution into well
    print(
        f"1. Pipetting  {instructions.solutions_corrected['edot']}ul of edot into well: {instructions.well_id}"
    )
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
    print("2. Performing CV with the following parameters:")
    print("\tCvvi = ", instructions.cv_initial_voltage)
    print("\tCVap1 = ", instructions.cv_first_anodic_peak)
    print("\tCVap2 = ", instructions.cv_second_anodic_peak)
    print("\tCVvf = ", instructions.cv_final_voltage)
    print("\tCVsr1 = ", instructions.cv_scan_rate_cycle_1)
    print("\tCvcycle = ", instructions.cv_cycle_count)
    try:
        characterization(
            char_instructions=instructions,
            char_results=instructions.results,
            wellplate=toolkit.wellplate,
        )
    except Exception as e:
        print("Error in characterization")
        print(e)
        print("Continuing with the rest of the experiment")

    finally:
        toolkit.mill.rinse_electrode()

    # Clear the well contents into waste
    print("3. Clearing well contents into waste")
    instructions.status = ExperimentStatus.CLEARING
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
    instructions.status = ExperimentStatus.RINSING
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
        1. Move lens over well B2
        2. Start recording
        3. Run cyclic
            Cvvi = 0
            CVap1 = -1.6 (this is intentionally negative)
            CVap2 = 0.4
            CVvf = -1.6
            CVsr1 = 0.025
            Cvcycle = 3
        4. Stop recording
        5. Save video

    """
    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 2 started"
    )

    # Move lens over well
    print(f"1. Moving lens over well {instructions.well_id}")
    instructions.status = ExperimentStatus.IMAGING
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["x"],
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id)["y"],
        z_coord=toolkit.wellplate.image_height,
        instrument=Instruments.LENS,
    )
    electrode_install = input("Confirm that the electrode is installed and ready to go. Press enter to continue\n")
    toolkit.global_logger.info("User confirmed electrode installation")
    pipette_lithium = input(
        "Manually pipette 120µL of 0.1M LiClO4 in water into well. Press enter to confirm"
    )
    toolkit.global_logger.info("User confirmed pipetting of lithium")

    # Start recording
    print("\n\n2. Starting recording")
    input("Start recording using the OBS software. Press enter to continue")

    # Run cyclic
    print("3. Running CV with the following parameters:")
    print("\tCvvi = 0")
    print("\tCVap1 = -1.6")
    print("\tCVap2 = 0.4")
    print("\tCVvf = -1.6")
    print("\tCVsr1 = 0.025")
    print("\tCvcycle = 3")
    characterization(
        char_instructions=instructions,
        char_results=instructions.results,
        wellplate=toolkit.wellplate,
    )

    # Stop recording
    print("4. Stopping recording")
    input("Stop recording using the OBS software. Press enter to continue")

    print(
        f"Experiment {instructions.project_id}.{instructions.project_campaign_id}.{instructions.id} part 2 complete"
    )
    print("*" * 80, end="\n\n")
