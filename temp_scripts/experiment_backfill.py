"""Backfilling experiment parameters and results"""

# pylint: disable=line-too-long
import json
from pathlib import Path

from panda_lib.experiment_class import (
    EchemExperimentBase,
    ExperimentResult,
    insert_experiment_parameters,
    insert_experiment_results,
    insert_experiments,
    select_experiment_information,
)

PARAMS_FOLDER = Path()
RESULTS_FOLDER = Path()
# Load in each json file in the PARAMS_FOLDER and insert the experiment parameters into the database
for file in PARAMS_FOLDER.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        protocol = data["protocol_type"]
    except KeyError:
        protocol = data["protocol_id"]

    try:
        JIRA = data["jira_issue_key"]
    except KeyError:
        JIRA = None
    # Build the experiment base
    experiment = EchemExperimentBase(
        experiment_id=data["id"],
        experiment_name=data["experiment_name"],
        protocol_id=protocol,
        priority=data["priority"],
        well_id=data["well_id"],
        pin=str(data["pin"]),
        project_id=data["project_id"],
        solutions=data["solutions"],
        solutions_corrected=data["solutions_corrected"],
        well_type_number=data["well_type_number"],
        pumping_rate=data["pumping_rate"],
        status=data["status"],
        status_date=data["status_date"],
        filename=data["filename"],
        project_campaign_id=data["project_campaign_id"],
        protocol_type=data["protocol_type"],
        plate_id=data["plate_id"],
        override_well_selection=data["override_well_selection"],
        process_type=data["process_type"],
        jira_issue_key=JIRA,
        ocp=data["ocp"],
        ca=data["ca"],
        cv=data["cv"],
        baseline=data["baseline"],
        flush_sol_name=data["flush_sol_name"],
        flush_vol=data["flush_vol"],
        mix_count=data["mix_count"],
        mix_volume=data["mix_volume"],
        rinse_count=data["rinse_count"],
        rinse_vol=data["rinse_vol"],
        ca_sample_period=data["ca_sample_period"],
        ca_prestep_voltage=data["ca_prestep_voltage"],
        ca_prestep_time_delay=data["ca_prestep_time_delay"],
        ca_step_1_voltage=data["ca_step_1_voltage"],
        ca_step_1_time=data["ca_step_1_time"],
        ca_step_2_voltage=data["ca_step_2_voltage"],
        ca_step_2_time=data["ca_step_2_time"],
        ca_sample_rate=data["ca_sample_rate"],
        char_sol_name=data["char_sol_name"],
        char_vol=data["char_vol"],
        cv_sample_period=data["cv_sample_period"],
        cv_initial_voltage=data["cv_initial_voltage"],
        cv_first_anodic_peak=data["cv_first_anodic_peak"],
        cv_second_anodic_peak=data["cv_second_anodic_peak"],
        cv_final_voltage=data["cv_final_voltage"],
        cv_step_size=data["cv_step_size"],
        cv_cycle_count=data["cv_cycle_count"],
        cv_scan_rate_cycle_1=data["cv_scan_rate_cycle_1"],
        cv_scan_rate_cycle_2=data["cv_scan_rate_cycle_2"],
        cv_scan_rate_cycle_3=data["cv_scan_rate_cycle_3"],
    )

    # Insert the experiment parameters
    # check if the experiment is already in the database
    experiment_exists = select_experiment_information(data["id"])
    if experiment_exists is None:
        insert_experiments(
            [
                experiment,
            ]
        )
        insert_experiment_parameters(experiment)
        print(f"Inserted experiment: {data['experiment_name']}")

# Load in each json file in the RESULTS_FOLDER and insert the experiment results into the database
for file in RESULTS_FOLDER.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build the experiment results
    if data["id"] != 10000874:
        continue
    result = ExperimentResult(experiment_id=data["id"], well_id=data["well_id"])

    result.set_ocp_cv_file(Path(data["ocp_char_files"][0]), True, 0.00)
    result.set_cv_data_file(Path(data["characterization_data_files"][0]))
    for file in data["image_files"]:
        result.append_image_file(file)

    # Insert the experiment results
    insert_experiment_results(result.to_results_records())
    print(f"Inserted results for experiment: {data['experiment_id']}")
