"""
Author: Gregory Robben
Date: 2025-01-14
Description: 3 series of experiments for PGMA-PAMA-phenol with 7mm wells, comparing the base used and the voltage of the CA.
"""

from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 20
EXPERIMENT_NAME = "grobben-01-11-pgma-pama-phenol-teaa-voltage-screening"
CAMPAIGN_ID = 1
PLATE_TYPE = 7  # 10 mm diameter wells on gold

voltages = [1.0, 1.5, 2.0]
replicates = 3


def main():
    """Runs the PGMA-PAMA-phenol experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    for voltage in voltages:
        for i in range(replicates):
            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id="grobben_01_12_pro",
                    well_id="A1",
                    plate_type_number=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID + i,
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
                    pumping_rate=0.5,
                    filename=str(experiment_id),
                    # Echem specific
                    ocp=1,
                    baseline=0,
                    cv=1,
                    ca=1,
                    ca_sample_period=0.1,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=voltage,
                    ca_step_1_time=1200,
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.5,
                    cv_step_size=0.002,
                    cv_first_anodic_peak=1.6,
                    cv_second_anodic_peak=0.0,
                    cv_scan_rate_cycle_1=0.025,
                    cv_scan_rate_cycle_2=0.025,
                    cv_scan_rate_cycle_3=0.025,
                    cv_cycle_count=3,
                    cv_initial_voltage=0.0,
                    cv_final_voltage=0.0,
                    cv_sample_period=0.1,
                    deposition_voltage=voltage,
                )
            )
            experiment_id += 1

    scheduler.add_nonfile_experiments(experiments)


if __name__ == "__main__":
    main()
