"""The sequence of steps for a pedotLHSv1_screening experiment."""

# Standard imports

# Non-standard imports
from panda_lib.actions.actions_default import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    Instruments,
    OCPFailure,
    __flush_v2,
    __forward_pipette_v2,
    chrono_amp,
    image_well,
    solution_selector,
    waste_selector,
)
from panda_lib.actions.actions_pedot import (
    chrono_amp_edot_bleaching,
    chrono_amp_edot_coloring,
    cyclic_volt_edot_characterizing,
)
from panda_lib.experiment_loop import Toolkit
from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.labware.vials import Vial2, read_vials
from panda_lib.utilities import correction_factor, solve_vials_ilp

PROTOCOL_ID = 999


def main(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function for the pedotLHSv1_screening function.
    This function is called by the ePANDA scheduler.
    It is the main function for the pedotLHSv1_screening protocol.
    """
    pedot_lhs_v1_screening(
        instructions=instructions,
        toolkit=toolkit,
    )


def pedot_lhs_v1_screening(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    The initial screening of the edot solution
    Per experiment:
    0. Apply correction factor to the programmed volumes
    1. pedotdeposition
    2. pedotbleaching
    3. pedotcoloring

    """

    pedotdeposition(
        instructions=instructions,
        toolkit=toolkit,
    )
    pedotbleaching(
        instructions=instructions,
        toolkit=toolkit,
    )
    pedotcoloring(
        instructions=instructions,
        toolkit=toolkit,
    )

    instructions.set_status_and_save(ExperimentStatus.COMPLETE)


def pedotdeposition(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing EDOT into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Rinsing the well 4x with rinse
    8. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_

    """
    toolkit.global_logger.info(
        "Running experimnet %s part 1", instructions.experiment_id
    )
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeDeposition")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info("1. Depositing EDOT into well: %s", instructions.well_id)

    # Determine the available edot stock vials and their concentrations
    # Calculate the combination of the available edot vials that will give the
    # desired concentration at the desired volume. Calculations are done using units of 20 ul
    # as that is our minimum pipetting volume. However once the calculations are done, the
    # actual volume to be pipetted is calculated using the correction factor.
    stock_vials, _ = read_vials()
    edot_vials: list[Vial2] = [
        vial for vial in stock_vials if vial.name == "edot" and vial.volume > 0
    ]

    # If there are no edot vials, raise an error
    if not edot_vials:
        toolkit.global_logger.error("No edot vials available")
        raise ValueError("No edot vials available")

    # There are one or more vials, let's calculate the volume to be pipetted from each
    # vial to get the desired volume and concentration
    edot_vial_volumes, deviation, edot_volumes_by_pos = solve_vials_ilp(
        # Concentrations of each vial in mM
        vial_concentration_map={
            vial.position: vial.concentration for vial in edot_vials
        },
        # Total volume to achieve in uL
        v_total=instructions.solutions["edot"],
        # Target concentration in mM
        c_target=instructions.edot_concentration,
    )

    # If the volumes are not found, raise an error
    if edot_vial_volumes is None:
        raise ValueError(
            f"No solution combinations found for edot {instructions.edot_concentration} mM"
        )
    toolkit.global_logger.info(
        "Volumes to draw from each edot vial: %s uL", edot_vial_volumes
    )
    toolkit.global_logger.info("Deviation from target concentration: %s mM", deviation)

    # Pipette the calculated volumes from the edot vials into the well
    for position, volume in edot_volumes_by_pos.items():
        if volume == 0:
            continue
        vial: Vial2 = next(vial for vial in edot_vials if vial.position == position)
        __forward_pipette_v2(
            volume=correction_factor(volume, vial.viscosity_cp),
            from_vessel=vial,
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
            pumping_rate=instructions.pumping_rate,
        )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)

    ## Move the electrode to the well
    # Move the electrode to above the well
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        z_coord=toolkit.wellplate.z_top,
        instrument=Instruments.ELECTRODE,
    )
    # Set the feed rate to 1000 to avoid splashing
    toolkit.mill.set_feed_rate(100)
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        z_coord=toolkit.wellplate.echem_height,
        instrument=Instruments.ELECTRODE,
    )
    # Set the feed rate back to 2000
    toolkit.mill.set_feed_rate(2000)

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

    # Rinse electrode
    toolkit.global_logger.info("4. Rinsing electrode")
    instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    __forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    __flush_v2(flush_solution_name="rinse", toolkit=toolkit)

    toolkit.global_logger.info("7. Rinsing the well 4x with rinse")
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(4):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of 4", i + 1)
        __forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=solution_selector(
                "rinse",
                correction_factor(120),
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
            pumping_rate=toolkit.pump.max_pump_rate,
        )
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.PIPETTE,
        )
        # Clear the well
        __forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                "waste",
                correction_factor(120),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("8. Take after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterDeposition",
    )
    instructions.process_type = 2
    instructions.priority = 1
    toolkit.global_logger.info("PEDOT deposition complete\n\n")


def pedotbleaching(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing liclo4 into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Take after image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s part 2", instructions.experiment_id
    )
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeBleaching")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    __forward_pipette_v2(
        volume=correction_factor(120),
        from_vessel=solution_selector(
            "liclo4",
            correction_factor(120),  # hard code this
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)

    ## Move the electrode to the well
    # Move the electrode to above the well
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        z_coord=toolkit.wellplate.z_top,
        instrument=Instruments.ELECTRODE,
    )
    # Set the feed rate to 1000 to avoid splashing
    toolkit.mill.set_feed_rate(100)
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        z_coord=toolkit.wellplate.echem_height,
        instrument=Instruments.ELECTRODE,
    )
    # Set the feed rate back to 2000
    toolkit.mill.set_feed_rate(2000)

    toolkit.global_logger.info("3. Performing CA")
    try:
        chrono_amp_edot_bleaching(instructions)
    except Exception as e:
        toolkit.global_logger.error(
            "Error occurred during chrono_amp bleaching: %s", str(e)
        )
        raise e

    # Rinse electrode
    toolkit.global_logger.info("4. Rinsing electrode")
    instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    __forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    __flush_v2(
        flush_solution_name="rinse",
        toolkit=toolkit,
    )

    toolkit.global_logger.info("7. Take after image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterBleaching",
    )

    instructions.process_type = 3
    instructions.priority = 0
    toolkit.global_logger.info("PEDOT bleaching complete\n\n")


def pedotcoloring(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing liclo4 into well
    2. Moving electrode to well
    3. Performing CA
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Take image of well

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s part 3", instructions.experiment_id
    )
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeColoring")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    __forward_pipette_v2(
        volume=correction_factor(120),
        from_vessel=solution_selector(
            "liclo4",
            correction_factor(120),
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate to 1000 to avoid splashing
        toolkit.mill.set_feed_rate(100)
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate back to 2000
        toolkit.mill.set_feed_rate(2000)

        toolkit.global_logger.info("3. Performing CA")
        try:
            chrono_amp_edot_coloring(instructions)
        except Exception as e:
            toolkit.global_logger.error(
                "Error occurred during chrono_amp coloring: %s", str(e)
            )
            raise e
    finally:
        pass

    # Rinse electrode
    toolkit.global_logger.info("4. Rinsing electrode")
    instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    __forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    __flush_v2(
        flush_solution_name="rinse",
        toolkit=toolkit,
        flush_count=3,
    )

    toolkit.global_logger.info("7. Take image of well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterColoring",
    )
    instructions.process_type = 4
    instructions.priority = 0
    toolkit.global_logger.info("PEDOT coloring complete\n\n")


def pedotcv(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing liclo4 into well
    2. Moving electrode to well
    3. Performing CV
    4. Rinsing electrode
    5. Clearing well contents into waste
    6. Flushing the pipette tip
    7. Take image of well
    8. Rinsing the well 4x with rinse
    9. Take end image

    Args:
        instructions (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s part 4", instructions.experiment_id
    )
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeCharacterizing")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    __forward_pipette_v2(
        volume=instructions.solutions["liclo4"],
        from_vessel=solution_selector(
            "liclo4",
            instructions.solutions["liclo4"],
        ),
        to_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        pumping_rate=instructions.pumping_rate,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", instructions.well_id)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate to 1000 to avoid splashing
        toolkit.mill.set_feed_rate(100)
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.echem_height,
            instrument=Instruments.ELECTRODE,
        )
        # Set the feed rate back to 2000
        toolkit.mill.set_feed_rate(2000)

        toolkit.global_logger.info("3. Performing CV")
        try:
            cyclic_volt_edot_characterizing(instructions)
        except Exception as e:
            toolkit.global_logger.error("Error occurred during chrono_amp: %s", str(e))
            raise e
    finally:
        toolkit.global_logger.info("4. Rinsing electrode")
        instructions.set_status_and_save(new_status=ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    toolkit.global_logger.info("5. Clearing well contents into waste")
    instructions.set_status_and_save(ExperimentStatus.CLEARING)
    __forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    __flush_v2(
        flush_solution_name="rinse",
        toolkit=toolkit,
        flush_count=3,
    )

    toolkit.global_logger.info("7. Take image of well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterCharacterizing",
    )
    toolkit.global_logger.info("8. Rinsing the well 4x with rinse")
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(4):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of 4", i + 1)
        __forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=solution_selector(
                "rinse",
                correction_factor(120),
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
            pumping_rate=toolkit.pump.max_pump_rate,
        )
        # Clear the well
        __forward_pipette_v2(
            volume=correction_factor(120),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                "waste",
                correction_factor(120),
            ),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("9. Take end image")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="EndImage",
    )
    instructions.process_type = 99
    instructions.priority = 99
    toolkit.global_logger.info("PEDOT characterizing complete\n\n")
