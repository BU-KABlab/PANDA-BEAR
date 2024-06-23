"""Generate the experiments for the edot voltage sweep"""

import json

from panda_lib import experiment_class
from panda_lib import wellplate
from panda_lib.config.config import read_testing_config
from panda_lib.scheduler import Scheduler, determine_next_experiment_id
from panda_lib.sql_tools.sql_system_state import get_current_pin

TEST: bool = read_testing_config()
CURRENT_PIN =  get_current_pin()

def main(
    project_id: int = None,
    experiment_name: str = None,
    campaign_id: int = None,
    pumping_rate: float = None,
    repetitions: int = None,
    starting_well: str = "F2",
):
    """
    Generate the experiments for the edot voltage sweep
    """
    print("TEST MODE: ", TEST)
    input("Press enter to continue")
    project_id: int = 16
    experiment_name = "edot potential screening"
    campaign_id: int = 2
    pumping_rate: float = 0.3
    repetitions: int = 1
    well_number: int = int(starting_well[1:])
    well_letter: str = starting_well[0]

    ca_step_1_voltages = [0.8, 1.0, 1.2, 1.4, 1.6]
    wellplate.load_new_wellplate(False, 107, 4)
    experiment_id = determine_next_experiment_id()
    experiments: list[experiment_class.EchemExperimentBase] = []

    for _ in range(repetitions):

        for dep_v in ca_step_1_voltages:
            experiments.append(
                experiment_class.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id=10,
                    well_id=str(well_letter) + str(well_number),
                    experiment_name=experiment_name + " " + "deposition",
                    priority=1,
                    pin=CURRENT_PIN,
                    project_id=project_id,
                    project_campaign_id=campaign_id,
                    solutions={"edot": 120, "liclo4": 0, "rinse": 120},
                    solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                    pumping_rate=pumping_rate,
                    status=experiment_class.ExperimentStatus.NEW,
                    filename=experiment_name + " " + str(experiment_id),
                    override_well_selection=0,  # 0 to use new wells only, 1 to reuse a well
                    process_type=1,
                    rinse_count=4,
                    rinse_vol=120,
                    # Echem specific
                    ocp=1,
                    baseline=0,
                    cv=0,
                    ca=1,
                    ca_sample_period=0.1,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=dep_v,
                    ca_step_1_time=30.0,
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.5,
                )
            )
            experiment_id += 1

            experiments.append(
                experiment_class.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id=10,
                    well_id=str(well_letter) + str(well_number),
                    experiment_name=experiment_name + " " + "bleaching",
                    priority=1,
                    pin=CURRENT_PIN,
                    project_id=project_id,
                    project_campaign_id=campaign_id,
                    solutions={"edot": 0, "liclo4": 120, "rinse": 0},
                    solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                    pumping_rate=pumping_rate,
                    status=experiment_class.ExperimentStatus.NEW,
                    filename=experiment_name + " " + str(experiment_id),
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
                    experiment_id=experiment_id,
                    protocol_id=10,
                    well_id=str(well_letter) + str(well_number),
                    experiment_name=experiment_name + " " + "coloring",
                    priority=1,
                    pin=CURRENT_PIN,
                    project_id=project_id,
                    project_campaign_id=campaign_id,
                    solutions={"edot": 0, "liclo4": 120, "rinse": 120},
                    solutions_corrected={"edot": 0, "liclo4": 0, "rinse": 0},
                    pumping_rate=pumping_rate,
                    status=experiment_class.ExperimentStatus.NEW,
                    filename=experiment_name + " " + str(experiment_id),
                    override_well_selection=1,
                    process_type=3,
                    rinse_count=4,
                    rinse_vol=120,
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
            well_number += 1

    for experiment in experiments:
        ## Print a recipt of the wellplate and its experiments noting the solution and volume
        print(f"Experiment name: {experiment.experiment_name}")
        print(f"Experiment id: {experiment.experiment_id}")
        print(f"Well id: {experiment.well_id}")
        print(f"Solutions: {json.dumps(experiment.solutions)}")
        print(f"Pumping rate: {pumping_rate}")
        print(
            f"Project campaign id: {experiment.project_id}.{experiment.project_campaign_id}\n"
        )
        print(f"CA Paramaters: {experiment.print_ca_parameters()}\n")
        print(f"CV Paramaters: {experiment.print_cv_parameters()}\n")

    # Add experiments to the queue and run them
    input("Press enter to add the experiments")
    scheduler = Scheduler()
    scheduler.add_nonfile_experiments(experiments)


if __name__ == "__main__":
    main()
