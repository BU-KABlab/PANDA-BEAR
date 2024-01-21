"""
Generates and prints out the experiment objects for the edot bleaching experiments
"""
import experiment_class
from config.pin import CURRENT_PIN
from config.config import TESTING
from scheduler import Scheduler
from wellplate import determine_next_experiment_id

print("TEST MODE: ", TESTING)
# Create experiments
COLUMNS = "ABCDEFGH"
ROWS = 12
PROJECT_ID = 16
PUMPING_RATE = 0.3
experiments_part1: list[experiment_class.EchemExperimentBase] = []
experiments_part2: list[experiment_class.EchemExperimentBase] = []


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
    WELL_NUMBER = 2
    CAMPAIGN_ID = 0
    EXPERIMENT_NAME = "edot_bleaching_part_1"

    experiment_id = determine_next_experiment_id()

    for i in range(1, 4):
        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                well_id="B" + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME,
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"edot": 120, "electrolyte": 120, "rinse0": 120},
                solutions_corrected={"edot": 120, "electrolyte": 120, "rinse0": 120},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + "_" + str(experiment_id),
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
        WELL_NUMBER += 1
    return experiments


def experiments_part_2() -> list[experiment_class.EchemExperimentBase]:
    """
    1. Move lens over well B2
    2. Start recording
    3. Run cyclic
        Cvvi = 0
        CVap1 = -1.6 (this is intentionally negative, we are scanning in the reverse direction as usual)
        CVap2 = 0.4
        CVvf = -1.6
        CVsr1 = 0.025
        Cvcycle = 3
    4. Stop recording
    """
    experiments = []
    WELL_NUMBER = 2
    CAMPAIGN_ID = 1
    EXPERIMENT_NAME = "edot_bleaching_part_2"
    experiment_id = determine_next_experiment_id()
    print(f"Experiment name: {EXPERIMENT_NAME}")

    for _ in range(1, 4):
        experiments.append(
            experiment_class.EchemExperimentBase(
                id=experiment_id,
                well_id="B" + str(WELL_NUMBER),
                experiment_name=EXPERIMENT_NAME,
                priority=1,
                pin=CURRENT_PIN,
                project_id=PROJECT_ID,
                project_campaign_id=CAMPAIGN_ID,
                solutions={"electrolyte": 0, "rinse0": 0},
                solutions_corrected={"electrolyte": 0, "rinse0": 0},
                pumping_rate=PUMPING_RATE,
                status=experiment_class.ExperimentStatus.NEW,
                filename=EXPERIMENT_NAME + "_" + str(experiment_id),
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
        WELL_NUMBER += 1

    return experiments


# for experiment in experiments_part1:
#     print(experiment.__str__())

# print("#"*50)
# for experiment in experiments_part2:
#     print(experiment.__str__())

if __name__ == "__main__":
    import controller

    # # Create scheduler
    scheduler = Scheduler()
    part1 = input("Run part 1? (y/n) ")

    if part1 == "y":
        part_1_experiments = experiments_part_1()
        for experiment in part_1_experiments:
            print(experiment.__str__())
        scheduler.add_nonfile_experiments(part_1_experiments)
        controller.main(part=1)
        print("Part 1 complete")
        print("#" * 50)
        print()
    else:
        print("Skipping part 1")

    electrode_install = input("Install electrode on lens. Press enter to confirm")
    print("User confirmed electrode installation")

    pipette_lithium = input(
        "Manually pipette 120µL of 0.1M LiClO4 in water into wells. Press enter to confirm"
    )
    print("User confirmed pipetting of lithium")

    part2 = input("Run part 2? (y/n) ")
    if part2 == "y":
        part_2_experiments = experiments_part_2()
        for experiment in part_2_experiments:
            print(experiment.__str__())
        scheduler.add_nonfile_experiments(part_2_experiments)
        controller.main(part=2)
    else:
        print("Skipping part 2")

    print("Experiments complete")
