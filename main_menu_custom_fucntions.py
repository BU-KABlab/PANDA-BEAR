"""
Custom PANDA_SDL menu options
"""
from pathlib import Path

from PIL import Image

from panda_lib import experiment_class, scheduler, utilities
from panda_lib.sql_tools import sql_system_state


def genererate_pedot_experiment():
    """Generates a PEDOT experiment."""
    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "generating PEDOT experiment"
    )
    import panda_experiment_analyzers.pedot as pedot_analysis
    from panda_experiment_analyzers.pedot.pedot_classes import PEDOTParams

    dep_v = float(input("Enter the deposition voltage: ").strip().lower())
    dep_t = float(input("Enter the deposition time: ").strip().lower())
    concentration = float(input("Enter the concentration: ").strip().lower())
    params = PEDOTParams(dep_v=dep_v, dep_t=dep_t, concentration=concentration)
    pedot_analysis.pedot_generator(params=params)


def generate_pedot_experiment_from_existing_data():
    """Generates an experiment from existing data using the ML model."""
    import panda_experiment_analyzers.pedot as pedot_analysis
    from panda_experiment_analyzers.pedot import sql_ml_functions
    from panda_experiment_analyzers.pedot.pedot_classes import (MLOutput,
                                                                PEDOTParams)

    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "generating experiment"
    )
    next_experiment = scheduler.determine_next_experiment_id()
    output = pedot_analysis.pedot_model(
        pedot_analysis.ml_file_paths.model_base_path,
        pedot_analysis.ml_file_paths.contourplots_path,
        next_experiment,
    )
    output = MLOutput(*output)
    params_for_next_experiment = PEDOTParams(
        dep_v=output.v_dep,
        dep_t=output.t_dep,
        concentration=output.edot_concentration,
    )
    # The ML Model will then make a prediction for the next experiment
    # First fetch and send the contour plot
    contour_plot = Path(
        experiment_class.select_specific_result(
            next_experiment, "PEDOT_Contour_Plots"
        ).result_value  # should only return one value
    )
    # Then fetch the ML results
    results_to_find = [
        "PEDOT_Deposition_Voltage",
        "PEDOT_Deposition_Time",
        "PEDOT_Concentration",
        "PEDOT_Predicted_Mean",
        "PEDOT_Predicted_Uncertainty",
    ]
    ml_results = []
    for result_type in results_to_find:
        ml_results.append(
            experiment_class.select_specific_result(
                next_experiment, result_type
            ).result_value  # should only return one value
        )
    # Compose message
    ml_results_msg = f"""
    Model #: {output.model_id}\n
    Experiment {next_experiment} Parameters and Predictions:\n
    Deposition Voltage: {ml_results[0]}\n
    Deposition Time: {ml_results[1]}\n
    Concentration: {ml_results[2]}\n
    Predicted Mean: {ml_results[3]}\n
    Predicted StdDev: {ml_results[4]}\n
    """
    print(ml_results_msg)

    img = Image.open(contour_plot)
    img.show()
    print(
        f"V_dep: {output.v_dep}, T_dep: {output.t_dep}, EDOT Concentration: {output.edot_concentration}"
    )
    keep_exp = (
        input("Would you like to add an experiment with these values? (y/n): ")
        .strip()
        .lower()
    )
    if keep_exp[0] == "y":
        pedot_analysis.pedot_generator(
            params_for_next_experiment,
            experiment_name="PEDOT_Optimization",
            campaign_id=0,
        )
    else:
        print("Experiment not added.")

        # Delete the contour plot files, and the model based on the model ID
        contour_plot.with_suffix(".png").unlink()
        contour_plot.with_suffix(".svg").unlink()
        model_name = (
            Path(pedot_analysis.ml_file_paths.model_base_path).name
            + f"_{output.model_id}"
        )
        model_path = Path(pedot_analysis.ml_file_paths.model_base_path)
        model_path = model_path.with_name(model_name).with_suffix(".pth")
        model_path.unlink()
        sql_ml_functions.delete_model(output.model_id)

    return


def analyze_pedot_experiment():
    """Analyzes a PEDOT experiment."""
    import panda_experiment_analyzers.pedot as pedot_analysis

    sql_system_state.set_system_status(
        utilities.SystemState.BUSY, "analyzing PEDOT experiment"
    )
    experiment_id = int(input("Enter the experiment ID to analyze: ").strip().lower())

    to_train = input("Train the model? (y/n): ").strip().lower()
    add_to_training_data = True if to_train[0] == "y" else False
    results = pedot_analysis.analyze(
        experiment_id, add_to_training_data=add_to_training_data
    )
    print(results)
