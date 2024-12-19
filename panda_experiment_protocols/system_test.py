"""The sequence of steps for a pedotLHSv1_screening experiment."""

# For writing a protocol, use the available actions from the panda_lib.actions module.
from panda_lib.actions import (
    ca_deposition,
    Toolkit,
    Hardware,
    Labware,
    ExperimentStatus,
)

# If you are using custom actions, import them from the appropriate module.
from panda_lib.actions_pedot import (
    chrono_amp_edot_bleaching,
    chrono_amp_edot_coloring,
    # cyclic_volt_edot_characterizing,
    PEDOTExperiment,
)

PROTOCOL_ID = 999
metadata = {
    "protocol_id": PROTOCOL_ID,
    "protocol_name": "PEDOT LHS v1 Screening",
    "protocol_description": "PEDOT LHS v1 Screening",
    "protocol_version": "1.0",
    "protocol_owner": "Harley Quinn",
    "protocol_owner_email": "hquinn@bu.edu",
    "protocol_owner_institution": "KABLab",
}

def run(
    experiment: PEDOTExperiment,
    hardware: Hardware,
    labware: Labware,
):
    """
    The initial screening of the edot solution
    Per experiment:
    1. pedotdeposition
    2. pedotbleaching
    3. pedotcoloring
    4. Save

    """
    toolkit = Toolkit(
        mill=hardware.mill,
        scale=hardware.scale,
        pump=hardware.pump,
        wellplate=labware.wellplate,
        global_logger=hardware.global_logger,
        experiment_logger=hardware.experiment_logger,
        flir_camera=hardware.flir_camera,
        arduino=hardware.arduino,
    )
    hardware.global_logger.info("Running experiment %s", experiment.experiment_id)
    hardware.global_logger.info(
        "Running experiment %s part 1 of 3", experiment.experiment_id
    )
    ca_deposition(
        soln_name="edot",
        exp_obj=experiment,
        toolkit=toolkit,
        rinse_well_at_end=True,
    )
    toolkit.global_logger.info(
        "Running experimnet %s part 2 of 3", experiment.experiment_id
    )
    ca_deposition(
        exp_obj=experiment,
        toolkit=toolkit,
        soln_name="liclo4",
        custom_deposition_function=chrono_amp_edot_bleaching,
        rinse_well_at_end=False,
    )
    toolkit.global_logger.info(
        "Running experiment %s part 3 of 3", experiment.experiment_id
    )
    ca_deposition(
        exp_obj=experiment,
        toolkit=toolkit,
        soln_name="liclo4",
        custom_deposition_function=chrono_amp_edot_coloring,
        rinse_well_at_end=False,
    )
    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


# def pedotcv(
#     instructions: PEDOTExperiment,
#     toolkit: Toolkit,
# ):
#     """
#     0. Imaging the well
#     1. Depositing liclo4 into well
#     2. Moving electrode to well
#     3. Performing CV
#     4. Rinsing electrode
#     5. Clearing well contents into waste
#     6. Flushing the pipette tip
#     7. Take image of well
#     8. Rinsing the well 4x with rinse
#     9. Take end image

#     Args:
#         instructions (EchemExperimentBase): _description_
#         toolkit (Toolkit): _description_
#     """
#     toolkit.global_logger.info(
#         "Running experiment %s part 4", instructions.experiment_id
#     )
#     instructions.declare_step(
#         "Imaging the well Before Characterization", ExperimentStatus.IMAGING
#     )
#     image_well(toolkit, instructions, "Before_Characterizing")

#     instructions.declare_step("Depositing liclo4", ExperimentStatus.DEPOSITING)
#     liclo4_volume = instructions.solutions["liclo4"]["volume"]
#     liclo4_concentration = instructions.solutions["liclo4"]["concentration"]

#     forward_pipette_v3(
#         volume=liclo4_volume,
#         src_vessel=solution_selector(
#             "liclo4",
#             liclo4_volume,
#         ),
#         dst_vessel=toolkit.wellplate.wells[instructions.well_id],
#         toolkit=toolkit,
#         source_concentration=liclo4_concentration,
#     )

#     ## Move the electrode to the well
#     instructions.declare_step("Moving electrode to well", ExperimentStatus.MOVING)
#     try:
#         ## Move the electrode to the well
#         # Move the electrode to above the well
#         toolkit.mill.safe_move(
#             x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
#             y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
#             z_coord=toolkit.wellplate.z_top,
#             instrument=Instruments.ELECTRODE,
#             second_z_cord=toolkit.wellplate.echem_height,
#             second_z_cord_feed=100,
#         )

#         instructions.declare_step("Performing CV", ExperimentStatus.CV)
#         try:
#             cyclic_volt_edot_characterizing(instructions)
#         except Exception as e:
#             toolkit.global_logger.error("Error occurred during chrono_amp: %s", str(e))
#             raise e
#     finally:
#         instructions.declare_step("Rinsing electrode", ExperimentStatus.ERINSING)
#         toolkit.mill.rinse_electrode(3)

#     # Clear the well
#     instructions.declare_step(
#         "Clearing well contents into waste", ExperimentStatus.CLEARING
#     )
#     forward_pipette_v3(
#         volume=toolkit.wellplate.wells[instructions.well_id].volume,
#         src_vessel=toolkit.wellplate.wells[instructions.well_id],
#         dst_vessel=waste_selector(
#             "waste",
#             toolkit.wellplate.wells[instructions.well_id].volume,
#         ),
#         toolkit=toolkit,
#     )

#     instructions.declare_step("Flushing the pipette tip", ExperimentStatus.FLUSHING)
#     flush_v3(
#         flush_solution_name=instructions.flush_sol_name,
#         flush_volume=instructions.flush_vol,
#         flush_count=instructions.flush_count,
#         toolkit=toolkit,
#     )

#     instructions.declare_step(
#         "Take image of well After_Characterizing", ExperimentStatus.IMAGING
#     )
#     image_well(
#         toolkit=toolkit,
#         instructions=instructions,
#         step_description="After_Characterizing",
#     )
#     instructions.declare_step(
#         f"Rinsing the well {instructions.rinse_count}x with rinse",
#         ExperimentStatus.RINSING,
#     )
#     rinse_v3(
#         instructions=instructions,
#         toolkit=toolkit,
#     )

#     instructions.declare_step("Take end image", ExperimentStatus.IMAGING)
#     image_well(
#         toolkit=toolkit,
#         instructions=instructions,
#         step_description="EndImage",
#     )
#     toolkit.global_logger.info("PEDOT characterizing complete\n\n")
