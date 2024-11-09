"""The sequence of steps for a pedotLHSv1_screening experiment."""

# For writing a protocol, use the available actions from the panda_lib.actions module.
from panda_lib.actions import (
    forward_pipette_v3,
    solution_selector,
    chrono_amp,
    waste_selector,
    image_well,
    flush_v2,
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
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeDeposition")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info("1. Depositing EDOT into well: %s", instructions.well_id)
    forward_pipette_v3(
        volume=instructions.solutions["edot"],
        src_vessel="edot",
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
        source_concentration=instructions.edot_concentration,
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
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(flush_solution_name="rinse", toolkit=toolkit)

    toolkit.global_logger.info("7. Rinsing the well 4x with rinse")
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(4):
        # Pipette the rinse solution into the well
        toolkit.global_logger.info("Rinse %d of 4", i + 1)
        forward_pipette_v3(
            volume=120,
            src_vessel=solution_selector(
                "rinse",
                120,
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
            volume=120,
            src_vessel=toolkit.wellplate.wells[instructions.well_id],
            dst_vessel=waste_selector(
                "waste",
                120,
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
        volume=120,
        src_vessel=solution_selector(
            "liclo4",
            120,  # hard code this
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
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
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
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
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeColoring")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    forward_pipette_v3(
        volume=120,
        src_vessel=solution_selector(
            "liclo4",
            120,
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
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
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
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
    toolkit.global_logger.info("0. Imaging the well")
    instructions.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, instructions, "BeforeCharacterizing")

    instructions.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    ## Deposit the experiment solution into the well
    toolkit.global_logger.info(
        "1. Depositing liclo4 into well: %s", instructions.well_id
    )
    forward_pipette_v3(
        volume=instructions.solutions_corrected["liclo4"],
        src_vessel=solution_selector(
            "liclo4",
            instructions.solutions_corrected["liclo4"],
        ),
        dst_vessel=toolkit.wellplate.wells[instructions.well_id],
        toolkit=toolkit,
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
    forward_pipette_v3(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        src_vessel=toolkit.wellplate.wells[instructions.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        toolkit=toolkit,
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    instructions.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_v2(
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
        forward_pipette_v3(
            volume=120,
            src_vessel=solution_selector(
                "rinse",
                120,
            ),
            dst_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
        )
        # Clear the well
        forward_pipette_v3(
            volume=120,
            src_vessel=toolkit.wellplate.wells[instructions.well_id],
            dst_vessel=waste_selector(
                "waste",
                120,
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
