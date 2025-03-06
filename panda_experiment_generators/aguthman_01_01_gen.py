"""
Author: Alex Guthman
Date: 2025-02-28
Description: Polyethylene transfer.
"""

from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase

PROJECT_ID = 22
EXPERIMENT_NAME = "aguthman_01_01-proof_of_concept"
PLATE_TYPE = 8

wells = ["C4", "C6", "C8", "E4", "E6", "E8","G4", "G6", "G8"]
def main():
    """Runs the PGMA-PAMA-phenol experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    for well in wells:
        experiments.append(
            EchemExperimentBase(
            experiment_id=experiment_id,
                protocol_id="aguthman_01_01",
                well_id=well,
                plate_type_number=PLATE_TYPE,
                experiment_name=EXPERIMENT_NAME,
                project_id=PROJECT_ID,
                project_campaign_id=0,
                solutions={
                    "polystyrene": {
                        "volume": 500,
                        "concentration": 1.0,
                        "repeated": 1,
                    },
                },
                flush_sol_name="ACNrinse",
                rinse_sol_name="ACNrinse",
                filename=str(experiment_id)+"aguthman_01_01",
                # Echem specific
                ocp=0,
                baseline=0,
                cv=0,
                ca=0,

            )
        )
    
        experiment_id += 1
    scheduler.schedule_experiments(experiments)