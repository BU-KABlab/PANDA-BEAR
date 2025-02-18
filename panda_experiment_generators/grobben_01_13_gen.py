"""
Author: Gregory Robben
Date: 2025-02-18
Description: 2 campaigns of 3 repeated experiments for modified and unmodieid PGMA-PAMA with 10mm wells.
"""

from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase

PROJECT_ID = 21
EXPERIMENT_NAME = "grobben-01-13-pgma-pama-teaa-validation"
PLATE_TYPE = 7  # 10 mm diameter wells on gold


def main():
    """Runs the PGMA-PAMA-phenol experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    experiments.append(
        EchemExperimentBase(
            experiment_id=experiment_id,
            protocol_id="grobben_01_13_pro",
            well_id="A1",
            plate_type_number=PLATE_TYPE,
            experiment_name=EXPERIMENT_NAME,
            project_id=PROJECT_ID,
            project_campaign_id=0,
            solutions={
                "pgma-pama-phenol-teaa-tbap": {
                    "volume": 320,
                    "concentration": 1.0,
                    "repeated": 1,
                },
                "DMFrinse": {
                    "volume": 160,
                    "concentration": 1.0,
                    "repeated": 5,
                },
                "ACNrinse": {
                    "volume": 160,
                    "concentration": 1.0,
                    "repeated": 9,
                },
            },
            flush_sol_name="ACNrinse",
            rinse_sol_name="ACNrinse",
            filename=str(experiment_id),
            # Echem specific
            ocp=1,
            baseline=0,
            cv=1,
            ca=0,

            # CV
            cv_step_size=0.002, 
            cv_first_anodic_peak=2.0,
            cv_second_anodic_peak=-0.1,
            cv_scan_rate_cycle_1=0.025,
            cv_scan_rate_cycle_2=0.025,
            cv_scan_rate_cycle_3=0.025,
            cv_cycle_count=10, 
            cv_initial_voltage=0.0,  # V
            cv_final_voltage=0.0, #V
            cv_sample_period=0.1,

        )
    )
    experiment_id += 1

    experiments.append(
        EchemExperimentBase(
            experiment_id=experiment_id,
            protocol_id="grobben_01_13_pro",
            well_id="A1",
            plate_type_number=PLATE_TYPE,
            experiment_name=EXPERIMENT_NAME,
            project_id=PROJECT_ID,
            project_campaign_id=1,
            solutions={
                "pgma-pama-teaa-tbap": {
                    "volume": 320,
                    "concentration": 1.0,
                    "repeated": 1,
                },
                "DMFrinse": {
                    "volume": 160,
                    "concentration": 1.0,
                    "repeated": 5,
                },
                "ACNrinse": {
                    "volume": 160,
                    "concentration": 1.0,
                    "repeated": 9,
                },
            },
            flush_sol_name="ACNrinse",
            rinse_sol_name="ACNrinse",
            filename=str(experiment_id),
            # Echem specific
            ocp=1,
            baseline=0,
            cv=1,
            ca=0,

            # CV
            cv_step_size=0.002, 
            cv_first_anodic_peak=2.0,
            cv_second_anodic_peak=-0.1,
            cv_scan_rate_cycle_1=0.025,
            cv_scan_rate_cycle_2=0.025,
            cv_scan_rate_cycle_3=0.025,
            cv_cycle_count=10, 
            cv_initial_voltage=0.0,  # V
            cv_final_voltage=0.0, #V
            cv_sample_period=0.1,

        )
    )
    experiment_id += 1

    scheduler.schedule_experiments(experiments)


if __name__ == "__main__":
    main()
