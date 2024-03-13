import json

import pandas as pd

from epanda_lib import experiment_class, wellplate
from epanda_lib.config.config import TESTING, WELL_HX
from epanda_lib.config.pin import CURRENT_PIN
from epanda_lib.scheduler import Scheduler

params_df = pd.read_csv(
    r"experiment_generators\exp_edot_screening_generator_v1_LHS_0,1.csv"
)  # Update path with location on PANDA computer


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True, sep="&")
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id = well_hx["experiment id"].max()
    return int(last_experiment_id + 1)

def main():
    TEST = TESTING
    print("TEST MODE: ", TEST)
    input("Press enter to continue")

    PROJECT_ID = 16
    EXPERIMENT_NAME = "pedotLHSv1_screening"
    CAMPAIGN_ID = 2
    PUMPING_RATE = 0.3

    # controller.load_new_wellplate(new_wellplate_type_number=6)
    wellplate.load_new_wellplate(False, 107, 4)
    experiment_id = determine_next_experiment_id()
    experiments: list[experiment_class.EchemExperimentBase] = []

    for index, row in params_df.iterrows():
        WELL_LETTER = row["well_letter"]
        WELL_NUMBER = row["well_number"]
        dep_V = row["dep_V"]  # dep_V is used for deposition voltage
        dep_T = row["dep_T"]  # dep_T is used for deposition time

        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                protocol_id=10,
                well_id=str(WELL_LETTER) + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME + " " + "Deposition",
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"edot": 120, "liclo4": 0, "rinse": 120},
                solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + " " + str(experiment_id),
                override_well_selection=0,  # 0 to use new wells only, 1 to reuse a well
                process_type=1,
                # Echem specific
                ocp=1,
                baseline=0,
                cv=0,
                ca=1,
                ca_sample_period=0.1,
                ca_prestep_voltage=0.0,
                ca_prestep_time_delay=0.0,
                ca_step_1_voltage=dep_V,
                ca_step_1_time=dep_T,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
            )
        )
        experiment_id += 1

        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                protocol_id=10,
                well_id=str(WELL_LETTER) + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME + " " + "bleaching",
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"edot": 0, "liclo4": 120, "rinse": 0},
                solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + " " + str(experiment_id),
                override_well_selection=1,
                process_type=2,
                # Echem specific
                ocp=1,
                baseline=0,
                cv=0,
                ca=1,
                ca_sample_period=0.1,
                ca_prestep_voltage=0.0,
                ca_prestep_time_delay=0.0,
                ca_step_1_voltage=-0.6,
                ca_step_1_time=60.0,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
            )
        )
        experiment_id += 1

        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                protocol_id=10,
                well_id=str(WELL_LETTER) + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME + " " + "coloring",
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"edot": 0, "liclo4": 120, "rinse": 120},
                solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + " " + str(experiment_id),
                override_well_selection=1,
                process_type=3,
                # Echem specific
                ocp=1,
                baseline=0,
                cv=0,
                ca=1,
                ca_sample_period=0.1,
                ca_prestep_voltage=0.0,
                ca_prestep_time_delay=0.0,
                ca_step_1_voltage=0.5,
                ca_step_1_time=60.0,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
            )
        )
        experiment_id += 1

        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                protocol_id=10,
                well_id=str(WELL_LETTER) + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME + " " + "char",
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"edot": 0, "liclo4": 120, "rinse": 120},
                solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + " " + str(experiment_id),
                override_well_selection=1,
                process_type=4,
                # Echem specific
                ocp=1,
                baseline=0,
                cv=1,
                ca=0,
                cv_step_size=0.002,
                cv_second_anodic_peak=-0.8,
                cv_first_anodic_peak=0.8,
                cv_scan_rate_cycle_1=0.04,
                cv_scan_rate_cycle_2=0.04,
                cv_scan_rate_cycle_3=0.04,
                cv_cycle_count=2,
                cv_initial_voltage=0.0,  # this should be the OCP final value
                cv_final_voltage=-0.8,
                cv_sample_period=0.1,
            )
        )
        experiment_id += 1
        WELL_NUMBER += 1


    for experiment in experiments:
        ## Print a recipt of the wellplate and its experiments noting the solution and volume
        print(f"Experiment name: {experiment.experiment_name}")
        print(f"Experiment id: {experiment.id}")
        print(f"Well id: {experiment.well_id}")
        print(f"Solutions: {json.dumps(experiment.solutions)}")
        print(f"Pumping rate: {PUMPING_RATE}")
        print(
            f"Project campaign id: {experiment.project_id}.{experiment.project_campaign_id}\n"
        )
        print(f"CA Paramaters: {experiment.print_ca_parameters()}\n")
        print(f"CV Paramaters: {experiment.print_cv_parameters()}\n")


    # Add experiments to the queue and run them
    input("Press enter to add the experiments")
    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)
