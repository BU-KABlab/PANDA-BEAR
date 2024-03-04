"""Generate the experiments for the edot voltage sweep"""

import json

import experiment_class
import wellplate
from config.config import TESTING
from config.pin import CURRENT_PIN
from scheduler import Scheduler, determine_next_experiment_id

TEST = TESTING
print("TEST MODE: ", TEST)
input("Press enter to continue")
# Create experiments
PROJECT_ID = 16
EXPERIMENT_NAME = "edot Initial Testing"
# print(f"Experiment name: {EXPERIMENT_NAME}")
CAMPAIGN_ID = 2
PUMPING_RATE = 0.3

# controller.load_new_wellplate(new_wellplate_type_number=6)
wellplate.load_new_wellplate(False, 107, 4)
experiment_id = determine_next_experiment_id()
experiments: list[experiment_class.EchemExperimentBase] = []
WELL_NUMBER = 2
WELL_LETTER = "F"
ca_step_1_voltages = [0.8, 1.0, 1.2, 1.4, 1.6]

for i in range(5):

    for dep_V in ca_step_1_voltages:
        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
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
                ca_step_1_time=30.0,
                ca_step_2_voltage=0.0,
                ca_step_2_time=0.0,
                ca_sample_rate=0.5,
            )
        )
        experiment_id += 1

    experiments.append(
        experiment_class.EchemExperimentBase(
            id=experiment_id,
            well_id=str(WELL_LETTER) + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME + " " + "Coloring",
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
            well_id=str(WELL_LETTER) + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME + " " + "Bleaching",
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
