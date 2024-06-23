"""
Generates and prints out the experiment objects for the edot bleaching experiments
"""
import experiment_class
from config.pin import CURRENT_PIN
from config.config import TESTING
from scheduler import Scheduler
from wellplate import determine_next_experiment_id

print("TEST MODE: ", TESTING)
if TESTING:
    input("Test mode is on. Press enter to continue or ctrl+c to quit")
    print("Continuing...")
else:
    input("Test mode is off. Press enter to continue or ctrl+c to quit")
    print("Continuing...")
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
PROJECT_ID = 16
PUMPING_RATE = 0.3

# Create 3 new experiments for the solution
def experiments_part_1() -> list[experiment_class.EchemExperimentBase]:
    """
    Experiment 1 - Deposition
            Pipette 120 µL of EDOT solution into well B2
            Run cyclic
                    Cvvi = 0
                    CVap1 = 2
                    CVap2 = 0.5
                    CVvf = 0.5
                    CVsr1 = 0.05
                    Cvcycle = 1
            Move EDOT solution from well B2 to waste
            Rinse pipette tip 3x with electrolyte rinse
            Rinse well 3x with electrolyte well rinse
            (well should be clear of solution)

    Experiment 2 - Deposition
            Pipette 120 µL of EDOT solution into well B3
            Run cyclic
                    Cvvi = 0
                    CVap1 = 2
                    CVap2 = 0.5
                    CVvf = 0.5
                    CVsr1 = 0.05
                    Cvcycle = 2
            Move EDOT solution from well B3 to waste
            Rinse pipette tip 3x with electrolyte rinse
            Rinse well 3x with electrolyte well rinse
            (well should be clear of solution)

    Experiment 3 - Deposition
            Pipette 120 µL of EDOT solution into well B4
            Run cyclic
            Cvvi = 0
            CVap1 = 2
            CVap2 = 0.5
            CVvf = 0.5
            CVsr1 = 0.05
            Cvcycle = 3
            Move EDOT solution from well B4 to waste
            Rinse pipette tip 3x with electrolyte rinse
            Rinse well 3x with electrolyte well rinse
            (well should be clear of solution)
    """
    experiments = []
    well_number = 2
    campaign_id = 0
    experiment_name = "edot_bleaching_part_1"

    experiment_id = determine_next_experiment_id()

    for i in range(1, 4):
        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                well_id="B" + str(well_number),
                experiment_name=experiment_name,
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=campaign_id,
                solutions={"edot": 120, "electrolyte": 120, "rinse0": 120},
                solutions_corrected={"edot": 120, "electrolyte": 120, "rinse0": 120},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=experiment_name + "_" + str(experiment_id),
                well_type_number=3,
                plate_id=107,
                # Echem specific
                baseline=0,
                cv=1,
                ca=0,
                ocp=1,
                cv_initial_voltage=0,
                cv_first_anodic_peak=2,
                cv_second_anodic_peak=0.5,
                cv_final_voltage=0.5,
                cv_cycle_count=i,
            )
        )
        experiment_id += 1
        well_number += 1
    return experiments


def experiments_part_2() -> list[experiment_class.EchemExperimentBase]:
    """
    1. Move lens over well B2
    2. Start recording
    3. Run cyclic
        Cvvi = 0
        CVap1 = -1.6 (this is intentionally negative)
        CVap2 = 0.4
        CVvf = -1.6
        CVsr1 = 0.025
        Cvcycle = 3
    4. Stop recording
    """
    experiments = []
    well_number = 2
    campaign_id = 1
    experiment_name = "edot_bleaching_part_2"
    experiment_id = determine_next_experiment_id()
    print(f"Experiment name: {experiment_name}")

    for _ in range(1, 4):
        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                well_id="B" + str(well_number),
                experiment_name=experiment_name,
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=campaign_id,
                solutions={"electrolyte": 0, "rinse0": 0},
                solutions_corrected={"electrolyte": 0, "rinse0": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=experiment_name + "_" + str(experiment_id),
                well_type_number=3,
                plate_id=107,
                # Echem specific
                baseline=0,
                cv=1,
                ca=0,
                ocp=1,
                cv_initial_voltage=0,
                cv_first_anodic_peak=-1.6,
                cv_second_anodic_peak=0.4,
                cv_final_voltage=-1.6,
                cv_scan_rate_cycle_1=0.025,
                cv_cycle_count=3,
            )
        )
        experiment_id += 1
        well_number += 1

    return experiments


if __name__ == "__main__":
    import controller
    print("""
Beginning edot bleaching experiments

Before starting, please ensure the following:
    1. The OBS software is open (pinned to the taskbar) to the FLIR scene
    2. The solutions are all uncapped and in the solutions file (located on the network drive)
    3. In the desktop folder, click on the slackbot shortcut to run the slackbot
    4. Confirm that your solutions are showing up as excpected by sending: "!epanda status" to the slackbot
    5. Confirm all equipment is connected and powered on
          
    NOTE: 
        - When recording with OBS it will use the start time as the file name. We can change this later if needed.

"""
)


    # # Create scheduler
    scheduler = Scheduler()
    print("Part 1: The program will only prompt you for confirmation during this part")
    part1 = input("Run part 1? (y/n) ")

    if part1 == "y":
        part_1_experiments = experiments_part_1()
        # for experiment in part_1_experiments:
        #     print(experiment.__str__())
        scheduler.add_nonfile_experiments(part_1_experiments)
        controller.main(part=1)
        print("Part 1 complete")
        print("#" * 80)
        print()
    else:
        print("Skipping part 1")

    print("Part 2:")
    print("""
The program will prompt you:
    - to install the elctrode to the lens AFTER homing the mill and BEFORE the first experiment
    - to pipette the lithium solution into the well
    - to start recording in OBS
    - to stop the recording in OBS
""")

    part2 = input("\nRun part 2? (y/n) ")
    print()
    if part2 == "y":
        part_2_experiments = experiments_part_2()
        # for experiment in part_2_experiments:
        #     print(experiment.__str__())
        scheduler.add_nonfile_experiments(part_2_experiments,override=True)
        controller.main(part=2)
    else:
        print("Skipping part 2")

    print("Experiments completed or skipped")
