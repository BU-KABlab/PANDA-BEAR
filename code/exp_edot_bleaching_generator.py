'''
Generates and prints out the experiment objects for the edot bleaching experiments
'''
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
EXPERIMENT_NAME = "edot_bleaching_part_1"
print(f"Experiment name: {EXPERIMENT_NAME}")
CAMPAIGN_ID = 0
PUMPING_RATE = 0.3
experiment_id = determine_next_experiment_id()
experiments_part1 : list[experiment_class.EchemExperimentBase]= []
experiments_part2 : list[experiment_class.EchemExperimentBase]= []
WELL_NUMBER = 2

# Create 3 new experiments for the solution
'''
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
'''

for i in range(1,4):
    experiments_part1.append(
        experiment_class.EchemExperimentBase(
            id=experiment_id,
            well_id='B' + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME,
            priority=1,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'edot': 120, 'electrolyte': 120, 'rinse0': 120},
            solutions_corrected={'edot': 120, 'electrolyte': 120, 'rinse0': 120},
            pumping_rate=PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + '_' + str(experiment_id),
            well_type_number=3,
            plate_id=107,

            # Echem specific
            baseline = 0,
            cv = 1,
            ca=0,
            ocp=1,
            cv_initial_voltage=0,
            cv_first_anodic_peak=2,
            cv_second_anodic_peak=0.5,
            cv_final_voltage=0.5,
            cv_cycle_count=i


        )
    )
    experiment_id += 1
    WELL_NUMBER += 1

WELL_NUMBER = 2
CAMPAIGN_ID += 1
EXPERIMENT_NAME = "edot_bleaching_part_2"
print(f"Experiment name: {EXPERIMENT_NAME}")

for i in range(1,4):
    experiments_part2.append(
        experiment_class.EchemExperimentBase(
            id=experiment_id,
            well_id='B' + str(WELL_NUMBER),
            experiment_name=EXPERIMENT_NAME,
            priority=1,
            pin=CURRENT_PIN,
            project_id=PROJECT_ID,
            project_campaign_id=CAMPAIGN_ID,
            solutions={'electrolyte': 0, 'rinse0': 0},
            solutions_corrected={'electrolyte': 0, 'rinse0': 0},
            pumping_rate=PUMPING_RATE,
            status=experiment_class.ExperimentStatus.NEW,
            filename=EXPERIMENT_NAME + '_' + str(experiment_id),
            well_type_number=3,
            plate_id=107,

            # Echem specific
            baseline = 0,
            cv = 1,
            ca=0,
            ocp=1,
            cv_initial_voltage=0,
            cv_first_anodic_peak=-1.6,
            cv_second_anodic_peak=0.4,
            cv_final_voltage=-1.6,
            cv_scan_rate_cycle_1=0.025,
            cv_cycle_count=3


        )
    )
    experiment_id += 1
    WELL_NUMBER += 1

for experiment in experiments_part1:
    print(experiment.__str__())

print("#"*50)
for experiment in experiments_part2:
    print(experiment.__str__())
# # Create scheduler
scheduler = Scheduler()

# Uncomment out the following line to add the part 1 experiments to the queue
# scheduler.add_nonfile_experiments(experiments_part1)

# Uncomment out the following line to add the part 2 experiments to the queue
# scheduler.add_nonfile_experiments(experiments_part2)
