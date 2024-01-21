'''
Experiment process
Experiment 1 - Deposition
	Pipette 120 µL of EDOT solution into well B2
	Run cyclic
		Cvvi = 0
		CVap1 = 2
		CVap2 = 0.5
		CVvf = 0.5
		CVsr1 = 0.05
		Cvcycle = 1
	Move EDOT solution from well B2 to waste
	Rinse pipette tip 3x with electrolyte rinse
	Rinse well 3x with electrolyte well rinse
	(well should be clear of solution)
	
Experiment 2 - Deposition
	Pipette 120 µL of EDOT solution into well B3
	Run cyclic
		Cvvi = 0
		CVap1 = 2
		CVap2 = 0.5
		CVvf = 0.5
		CVsr1 = 0.05
		Cvcycle = 2
	Move EDOT solution from well B3 to waste
	Rinse pipette tip 3x with electrolyte rinse
	Rinse well 3x with electrolyte well rinse
	(well should be clear of solution)
	
Experiment 3 - Deposition
	Pipette 120 µL of EDOT solution into well B4
	Run cyclic
	Cvvi = 0
	CVap1 = 2
	CVap2 = 0.5
	CVvf = 0.5
	CVsr1 = 0.05
	Cvcycle = 3
	Move EDOT solution from well B4 to waste
	Rinse pipette tip 3x with electrolyte rinse
	Rinse well 3x with electrolyte well rinse
	(well should be clear of solution)
	
PAUSE
Install electrode on lens - user confirm
Manually pipette 120µL of 0.1M LiClO4 in water into well B2 - user confirm
RESUME - user confirm

Experiment 1b - Characterization
	Move lens over well B2
	Start recording
	Run cyclic
		Cvvi = 0
		CVap1 = -1.6 (this is intentionally negative, we are scanning in the reverse direction as usual)
		CVap2 = 0.4
		CVvf = -1.6
		CVsr1 = 0.025
		Cvcycle = 3
	Stop recording
	Save video
	
PAUSE
Manually pipette 120µL of 0.1M LiClO4 in water into well B3 - user confrim
RESUME

Experiment 2b - Characterization
	Move lens over well B3
	Start recording
	Run cyclic
		Cvvi = 0
		CVap1 = -1.6
		CVap2 = 0.4
		CVvf = -1.6
		CVsr1 = 0.025
		Cvcycle = 3
	Stop recording
	Save video
	
PAUSE
Manually pipette 120µL of 0.1M LiClO4 in water into well B4
RESUME

Experiment 3b - Characterization
	Move lens over well B4
	Start recording
	Run cyclic
		Cvvi = 0
		CVap1 = -1.6
		CVvf = -1.6
		CVsr1 = 0.025
		Cvcycle = 3
	Stop recording
	Save video

Notes:
-   All depositions are CVs, using the same settings EXCEPT number of cycles.
-   All characterizations are CVs, using different settings than the depositions, 
    but the same settings for all characterizations.
-   The characterization solutions are pipetted in manually right before each 
    experiment because of how long the characterization CVs will take 
    (we are minimizing the evaporation of the solution).
'''
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
from experiment_class import EchemExperimentBase
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
        5 .Rinse well 4x with electrolyte well rinse
        (well should be clear of solution)

    """
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

    print("Experiment %d part 1 started", instructions.id)
    print("Deposition using CV")
    # Pipette 120ul of edot solution into well
    print("1. Pipetting 120ul of edot into well: ", instructions.well_id)
    forward_pipette_v2(
        volume=instructions.solutions_corrected['edot'],
        from_vessel=solution_selector(
            stock_vials,
            'edot',
            instructions.solutions_corrected['edot'],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Perform CV
    print("2. Performing CV with the following parameters:")
    print("\tCvvi = ", instructions.cv_initial_voltage)
    print("\tCVap1 = ", instructions.cv_first_anodic_peak)
    print("\tCVap2 = ", instructions.cv_second_anodic_peak)
    print("\tCVvf = ", instructions.cv_final_voltage)
    print("\tCVsr1 = ", instructions.cv_scan_rate_cycle_1)
    print("\tCvcycle = ", instructions.cv_cycle_count)

    characterization(
        char_instructions=instructions,
        char_results=instructions.results,
        mill=toolkit.mill,
        wellplate=toolkit.wellplate,
    )

    # Clear the well contents into waste
    print("3. Clearing well contents into waste")
    forward_pipette_v2(
        volume=instructions.solutions_corrected['edot'],
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            'waste',
            instructions.solutions_corrected['edot'],
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
        pumping_rate=instructions.pumping_rate,
    )

    # Image the cleared well
    # image_well(
    #     wellplate=toolkit.wellplate,
    #     instructions=instructions,
    #     toolkit=toolkit,
    #     step_description='cleared',
    # )

    # Flush the pipette tip x3 with electrolyte rinse
    print("4. Flushing pipette tip with electrolyte rinse")
    for _ in range(3):
        forward_pipette_v2(
            volume=instructions.solutions_corrected['electrolyte_rinse'],
            from_vessel=solution_selector(
                stock_vials,
                'electrolyte_rinse',
                instructions.solutions_corrected['electrolyte_rinse'],
            ),
            to_vessel=waste_selector(
                waste_vials,
                'waste',
                instructions.solutions_corrected['electrolyte_rinse'],
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

    # Rinse the well 4x with electrolyte rinse
    print("5. Rinsing well 4x with electrolyte well rinse")
    for _ in range(4):
        forward_pipette_v2(
            volume=instructions.solutions_corrected['electrolyte_rinse'],
            from_vessel=solution_selector(
                stock_vials,
                'electrolyte_rinse',
                instructions.solutions_corrected['electrolyte_rinse'],
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )

        forward_pipette_v2(
            volume=instructions.solutions_corrected['electrolyte_rinse'],
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                waste_vials,
                'waste',
                instructions.solutions_corrected['electrolyte_rinse'],
            ),
            pump=toolkit.pump,
            mill=toolkit.mill,
            pumping_rate=instructions.pumping_rate,
        )
    # Image the rinsed well
    # image_well(
    #     wellplate=toolkit.wellplate,
    #     instructions=instructions,
    #     toolkit=toolkit,
    #     step_description='rinsed',
    # )

    toolkit.mill.rest_electrode()
    print("Experiment %d part 1 complete", instructions.id)

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
            CVap1 = -1.6 (this is intentionally negative, we are scanning in the reverse direction as usual)
            CVap2 = 0.4
            CVvf = -1.6
            CVsr1 = 0.025
            Cvcycle = 3
        4. Stop recording
        5. Save video

    """
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

    # Move lens over well
    print("1. Moving lens over well")
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.wells[instructions.well_id]['x'],
        y_coord=toolkit.wellplate.wells[instructions.well_id]['y'],
        z_coord=toolkit.wellplate.image_height,
        instrument= Instruments.LENS
    )
    # Start recording
    print("2. Starting recording")
    input("Start recording using the SpinView software. Press enter to continue")

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
        mill=toolkit.mill,
        wellplate=toolkit.wellplate,
    )

    # Stop recording
    print("4. Stopping recording")
    input("Stop recording using the SpinView software. Press enter to continue")

    toolkit.mill.rest_electrode()

    print("Experiment %d part 2 complete", instructions.id)


def edot_bleaching_protocol(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol to test the bleaching of EDOT in the wellplate

    Steps:
    Part 1:
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
        5 .Rinse well 4x with electrolyte well rinse
        (well should be clear of solution)

    PAUSE
    Install electrode on lens - user confirm
    Manually pipette 120µL of 0.1M LiClO4 in water into well B2 - user confirm
    RESUME - user confirm

    Part 2:
        1. Move lens over well B2
        2. Start recording
        3. Run cyclic
            Cvvi = 0
            CVap1 = -1.6 (this is intentionally negative, we are scanning in the reverse direction as usual)
            CVap2 = 0.4
            CVvf = -1.6
            CVsr1 = 0.025
            Cvcycle = 3
        4. Stop recording
        5. Save video

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        toolkit (Toolkit object): The toolkit object which contains the pump, mill, and wellplate
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    """
    edot_bleaching_part_1(
        instructions=instructions,
        toolkit=toolkit,
        stock_vials=stock_vials,
        waste_vials=waste_vials,
    )

    electrode_install = input("Install electrode on lens. Press enter to confirm")
    toolkit.global_logger.info("User confirmed electrode installation")

    pipette_lithium = input("Manually pipette 120µL of 0.1M LiClO4 in water into well %s. Press enter to confirm", instructions.well_id)
    toolkit.global_logger.info("User confirmed pipetting of lithium")

    input("Press enter to continue")

    edot_bleaching_part_2(
        instructions=instructions,
        toolkit=toolkit,
        stock_vials=stock_vials,
        waste_vials=waste_vials,
    )

    print("Experiment %d complete", instructions.id)

    electrode_removal = input("Remove electrode from lens. Press enter to confirm")
    toolkit.global_logger.info("User confirmed electrode removal after experiment %d", instructions.id)

    input("Press enter to continue")

    