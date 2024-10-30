"""The sequence of steps for a PGMA experiment."""

# Solutions needed
# 1 - PGMA-phenol
# 2 - DMFc + PEG-FC (referred to as FC)
# Rinse solutions needed
# 1 - DMF-TBAP
# 2 - DMF
# 3 - acetonitrile
# Steps
# Pre-characterization
# image
# dispense solution 2
# CV pre-characterization
# rinse well DMF-TBAP
# image
# Deposition
# dispense solution 1
# CA deposition (vary the time and voltage)
# rinse well DMF-TBAP
# image
# Post-characterization
# dispense solution 2
# CV post-characterization
# rinse well DMF
# rinse well acetonitrile
# image


# Non-standard imports
from panda_lib.controller import Toolkit
from panda_lib.actions import (
    forward_pipette_v2,
    solution_selector,
    chrono_amp,
    waste_selector,
    image_well,
    flush_v2,
    OCPFailure,
    CAFailure,
    CVFailure,
    DepositionFailure,
    Instruments
)
from panda_lib.actions_pgma import cyclic_volt_pgma_fc
from panda_lib.experiment_class import PGMAExperiment, ExperimentStatus
from panda_lib.correction_factors import correction_factor


def main(
    instructions: PGMAExperiment,
    toolkit: Toolkit,
    **kwargs,
):
    """
    Wrapper function for the PGMA_dep_v2_screening function.
    This function is called by the PANDA scheduler.
    It is the main function for the PGMA_dep_v2_screening protocol.
    """
    PGMA_dep_v2_screening(
        instructions=instructions,
        toolkit=toolkit,
    )


def PGMA_dep_v2_screening(
    instructions: PGMAExperiment,
    toolkit: Toolkit,
):
    """
    The initial screening of the PGMA solution
    Per experiment:
    0. Apply correction factor to the programmed volumes
    1. FC_prechar
    2. PGMAdeposition
    3. FC_postchar

    """
    # Apply correction factor to the programmed volumes
    toolkit.global_logger.info("Applying correction factor to the programmed volumes")
    for solution in instructions.solutions:
        instructions.solutions_corrected[solution] = correction_factor(
            instructions.solutions[solution],
            solution_selector(
                solution,  # The solution name
                instructions.solutions[solution],  # The volume of the solution
            ).viscosity_cp,
        )

    # Run the experiment based on its experiment type
    FC_prechar(
        instructions=instructions,
        toolkit=toolkit,
    )
    PGMAdeposition(
        instructions=instructions,
        toolkit=toolkit,
    )
    FC_postchar(
        instructions=instructions,
        toolkit=toolkit,
    )

    instructions.set_status(ExperimentStatus.COMPLETE)


def PGMAdeposition(
    instructions: PGMAExperiment,
    toolkit: Toolkit,
):
    """
    1. Depositing PGMA into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Rinsing the well 4x with rinse
    8. Take film after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """
    solution_name = "PGMA-phenol"
    solution_name = solution_name.lower()
    current_well = toolkit.wellplate.wells[instructions.well_id]
    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing %s into well: %s", solution_name, instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected[solution_name],
        from_vessel=solution_selector(
            solution_name,
            instructions.solutions_corrected[solution_name],
        ),
        to_vessel=current_well,
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        toolkit.global_logger.info("3. Performing CA deposition")
        try:
            chrono_amp(instructions, file_tag="CA_deposition")

        except (OCPFailure, CAFailure, CVFailure, DepositionFailure) as e:
            toolkit.global_logger.error("Error occurred during chrono_amp: %s", str(e))
            raise e
        except Exception as e:
            toolkit.global_logger.error(
                "Unknown error occurred during chrono_amp: %s", str(e)
            )
            raise e
    finally:
        toolkit.global_logger.info("3b. Rinsing electrode")
        instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("4a. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=current_well.volume,
        from_vessel=current_well,
        to_vessel=waste_selector(
            "waste",
            current_well.volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("4b. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
        flush_solution_name="DMF-TBAPrinse",
        toolkit=toolkit,
    )

    toolkit.global_logger.info("5. Rinsing the well 4x with rinse")
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(4):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of 4", i + 1)
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=solution_selector(
                "DMF-TBAPrinse",
                correction_factor(320),
            ),
            to_vessel=current_well,
            toolkit=toolkit,
            pumping_rate=instructions.pumping_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=current_well,
            to_vessel=waste_selector(
                "waste",
                correction_factor(320),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("6. Take after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "AfterDepDry")
    toolkit.global_logger.info("PGMA deposition complete")
    print("\n\n")


def FC_prechar(
    instructions: PGMAExperiment,
    toolkit: Toolkit,
):
    """
    1. Take before image
    2. Dispense DMFc-PEG-FC into well
    3. Move electrode to well
    4. Perform CV
    5. Rinse electrode
    6. Clear well contents into waste
    7. Flush the pipette tip
    8. Rinse with DMF-TBAP
    9. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """
    solution_name = "fc"
    solution_name = solution_name.lower()
    current_well = toolkit.wellplate.wells[instructions.well_id]

    toolkit.global_logger.info("1. Take before image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BareWell")

    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "2. Dispensing %s into well: %s", solution_name, instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected[solution_name.lower()],
        from_vessel=solution_selector(
            solution_name,
            instructions.solutions_corrected[solution_name],
        ),
        to_vessel=current_well,
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("3a. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        toolkit.global_logger.info("3b. Performing CV")
        try:
            cyclic_volt_pgma_fc(instructions, file_tag="FC_prechar")
        except Exception as e:
            toolkit.global_logger.error("Error occurred during FC CV: %s", str(e))
            raise e
    finally:
        toolkit.global_logger.info("3c. Rinsing electrode")
        instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("3d. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=current_well.volume,
        from_vessel=current_well,
        to_vessel=waste_selector(
            "waste",
            current_well.volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("4a. Flushing the pipette tip with DMF-TBAPrinse")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
        flush_solution_name="DMF-TBAPrinse",
        toolkit=toolkit,
    )

    toolkit.global_logger.info("4b. Rinsing the well 4x with DMF-TBAPrinse")
    for _ in range(4):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=solution_selector(
                "DMF-TBAPrinse",
                correction_factor(320),
            ),
            to_vessel=current_well,
            toolkit=toolkit,
            pumping_rate=instructions.pumping_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=current_well,
            to_vessel=waste_selector(
                "waste",
                correction_factor(320),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("5. Take after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterPreCV",
    )
    instructions.set_status(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("FC Pre-CV complete")
    print("\n\n")


def FC_postchar(
    instructions: PGMAExperiment,
    toolkit: Toolkit,
):
    """
    1. Dispensing DMFc-PEG-FC into well
    2. Moving electrode to well
    3. Performing CV
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Rinsing with DMF
    8. Rinsing with acetonitrile
    9. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
    """
    solution_name = "FC"
    solution_name = solution_name.lower()
    current_well = toolkit.wellplate.wells[instructions.well_id]
    instructions.set_status(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing %s into well: %s", solution_name, instructions.well_id
    )
    forward_pipette_v2(
        volume=instructions.solutions_corrected[solution_name],
        from_vessel=solution_selector(
            solution_name,
            instructions.solutions_corrected[solution_name],
        ),
        to_vessel=current_well,
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2a. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        toolkit.global_logger.info("2b. Performing CV")
        try:
            cyclic_volt_pgma_fc(instructions, file_tag="FC_postchar")
        except Exception as e:
            toolkit.global_logger.error("Error occurred during FC CV: %s", str(e))
            raise e
    finally:
        toolkit.global_logger.info("2c. Rinsing electrode")
        instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("2d. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    forward_pipette_v2(
        volume=current_well.volume,
        from_vessel=current_well,
        to_vessel=waste_selector(
            "waste",
            current_well.volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("3a. Flushing the pipette tip with DMFrinse")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
        flush_solution_name="DMFrinse",
        toolkit=toolkit,
    )

    toolkit.global_logger.info("3b. Rinsing the well 4x with DMFrinse")
    for _ in range(4):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=solution_selector(
                "DMFrinse",
                correction_factor(320),
            ),
            to_vessel=current_well,
            toolkit=toolkit,
            pumping_rate=instructions.pumping_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=current_well,
            to_vessel=waste_selector(
                "waste",
                correction_factor(320),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("4a. Flushing the pipette tip with ACNrinse")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
        flush_solution_name="ACNrinse",
        toolkit=toolkit,
    )
    toolkit.global_logger.info("4b. Rinsing the well 4x with ACNrinse")
    for _ in range(4):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=solution_selector(
                "ACNrinse",
                correction_factor(320),
            ),
            to_vessel=current_well,
            toolkit=toolkit,
            pumping_rate=instructions.pumping_rate,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(320),
            from_vessel=current_well,
            to_vessel=waste_selector(
                "waste",
                correction_factor(320),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("5. Take after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterCV",
    )
    instructions.set_status(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("FC CV complete")
    print("\n\n")
