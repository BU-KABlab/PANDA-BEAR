"""The sequence of steps for a pedotLHSv1_screening experiment."""

# For writing a protocol, use the available actions from the panda_lib.actions module.
from panda_lib.actions import (
    forward_pipette_v3,
    solution_selector,
    chrono_amp,
    waste_selector,
    image_well,
    flush_v3,
    OCPFailure,
    CAFailure,
    CVFailure,
    DepositionFailure,
    Instruments,
    Toolkit,
    ExperimentStatus,
)

# If you are using custom actions, import them from the appropriate module.
from panda_lib.actions_pedot import (
    chrono_amp_edot_bleaching,
    chrono_amp_edot_coloring,
    cyclic_volt_edot_characterizing,
    PEDOTExperiment,
)

PROTOCOL_ID = 999


def main(
    instructions: PEDOTExperiment,
    toolkit: Toolkit,
):
    """
    The initial screening of the edot solution
    Per experiment:
    1. pedotdeposition
    2. pedotbleaching
    3. pedotcoloring
    4. Save

    """
    pedotdeposition(instructions=instructions, toolkit=toolkit)
    pedotbleaching(instructions=instructions, toolkit=toolkit)
    pedotcoloring(instructions=instructions, toolkit=toolkit)
    instructions.set_status_and_save(ExperimentStatus.COMPLETE)


def pedotdeposition(
    instructions: PEDOTExperiment,
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
    instructions.declare_step("Imaging the well Before Deposition", ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeDeposition")
    instructions.declare_step("Depositing EDOT into well", ExperimentStatus.DEPOSITING)
    forward_pipette_v3(
        volume=instructions.solutions["edot"]["volume"],
        src_vessel="edot",
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        source_concentration=instructions.solutions["edot"]["concentration"],
    )

    ## Move the electrode to the well
    instructions.declare_step("Moving electrode to well", ExperimentStatus.MOVING)

    ## Move the electrode to the well
    # Move the electrode to above the well
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        z_coord=toolkit.wellplate.z_top,
        instrument=Instruments.ELECTRODE,
        second_z_cord=toolkit.wellplate.echem_height,
        second_z_cord_feed=100,
    )

    instructions.declare_step("Performing CA", ExperimentStatus.CA)
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
    instructions.declare_step("Rinsing electrode", ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    instructions.declare_step("Clearing well contents into waste", ExperimentStatus.CLEARING)
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    instructions.declare_step("Flushing the pipette tip", ExperimentStatus.FLUSHING)
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v3(
        flush_solution_name=instructions.flush_sol_name,
        flush_volume=instructions.flush_vol,
        flush_count=instructions.flush_count,
        toolkit=toolkit,
    )

    instructions.declare_step(f"Rinsing the well {instructions.rinse_count}x with rinse",ExperimentStatus.RINSING)
    for i in range(instructions.rinse_count):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of %d", i + 1, instructions.rinse_count)
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel=solution_selector(
                "rinse",
                instructions.rinse_vol,
            ),
            dst_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
        )
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.PIPETTE,
        )
        # Clear the well
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel=toolkit.wellplate.wells[instructions.well_id],
            dst_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    instructions.declare_step("Take after deposition image", ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterDeposition",
    )
    toolkit.global_logger.info("PEDOT deposition complete\n\n")


def pedotbleaching(
    instructions: PEDOTExperiment,
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
    forward_pipette_v3(
        volume=instructions.solutions["liclo4"]["volume"],
        src_vessel=solution_selector(
            "liclo4",
            instructions.solutions["edot"]["volume"],  # hard code this
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        source_concentration=instructions.solutions["liclo4"]["concentration"],
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
        second_z_cord=toolkit.wellplate.echem_height,
        second_z_cord_feed=100,
    )
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
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    instructions.declare_step("Flushing the pipette tip", ExperimentStatus.FLUSHING)
    flush_v3(
        flush_solution_name="rinse",
        toolkit=toolkit,
    )

    instructions.declare_step("Take after bleaching image", ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterBleaching",
    )

    instructions.process_type = 3
    instructions.priority = 0
    toolkit.global_logger.info("PEDOT bleaching complete\n\n")


def pedotcoloring(
    instructions: PEDOTExperiment,
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
    instructions.declare_step("Imaging the well Before Coloring", ExperimentStatus.IMAGING)

    image_well(toolkit, instructions, "BeforeColoring")

    instructions.declare_step("Depositing liclo4", ExperimentStatus.DEPOSITING)
    forward_pipette_v3(
        volume=instructions.solutions["liclo4"]["volume"],
        src_vessel=solution_selector(
            "liclo4",
            instructions.solutions["liclo4"]["volume"],
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        source_concentration=instructions.solutions["liclo4"]["concentration"],
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
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

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
    instructions.declare_step("Rinsing electrode", ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    # Clear the well
    instructions.declare_step("Clearing well contents into waste", ExperimentStatus.CLEARING)
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    instructions.declare_step("Flushing the pipette tip", ExperimentStatus.FLUSHING)
    flush_v3(
        flush_solution_name=instructions.flush_sol_name,
        toolkit=toolkit,
        flush_count=instructions.flush_count,
        flush_volume=instructions.flush_vol,
    )

    instructions.declare_step("Take image of well AfterColoring", ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="AfterColoring",
    )
    toolkit.global_logger.info("PEDOT coloring complete\n\n")


def pedotcv(
    instructions: PEDOTExperiment,
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
    instructions.declare_step(
        "Imaging the well Before Characterization", ExperimentStatus.IMAGING
    )
    image_well(toolkit, instructions, "Before_Characterizing")

    instructions.declare_step("Depositing liclo4", ExperimentStatus.DEPOSITING)
    liclo4_volume = instructions.solutions["liclo4"]["volume"]
    liclo4_concentration = instructions.solutions["liclo4"]["concentration"]

    forward_pipette_v3(
        volume=liclo4_volume,
        src_vessel=solution_selector(
            "liclo4",
            liclo4_volume,
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        source_concentration=liclo4_concentration,
    )

    ## Move the electrode to the well
    instructions.declare_step("Moving electrode to well", ExperimentStatus.MOVING)
    try:
        ## Move the electrode to the well
        # Move the electrode to above the well
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.ELECTRODE,
            second_z_cord=toolkit.wellplate.echem_height,
            second_z_cord_feed=100,
        )

        instructions.declare_step("Performing CV", ExperimentStatus.CV)
        try:
            cyclic_volt_edot_characterizing(instructions)
        except Exception as e:
            toolkit.global_logger.error("Error occurred during chrono_amp: %s", str(e))
            raise e
    finally:
        instructions.declare_step("Rinsing electrode", ExperimentStatus.ERINSING)
        toolkit.mill.rinse_electrode(3)

    # Clear the well
    instructions.declare_step(
        "Clearing well contents into waste", ExperimentStatus.CLEARING
    )
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    instructions.declare_step("Flushing the pipette tip", ExperimentStatus.FLUSHING)
    flush_v3(
        flush_solution_name=instructions.flush_sol_name,
        flush_volume=instructions.flush_vol,
        flush_count=instructions.flush_count,
        toolkit=toolkit,
    )

    instructions.declare_step(
        "Take image of well After_Characterizing", ExperimentStatus.IMAGING
    )
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="After_Characterizing",
    )
    instructions.declare_step(
        f"Rinsing the well {instructions.rinse_count}x with rinse",
        ExperimentStatus.RINSING,
    )
    for i in range(instructions.rinse_count):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of %d", i + 1, instructions.rinse_count)
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel=solution_selector(
                "rinse",
                instructions.rinse_vol,
            ),
            dst_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
        )
        # Clear the well
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel=toolkit.wellplate.wells[instructions.well_id],
            dst_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    instructions.declare_step("Take end image", ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        instructions=instructions,
        step_description="EndImage",
    )
    toolkit.global_logger.info("PEDOT characterizing complete\n\n")
