"""
Author: Gregory Robben
Date: 2025-01-14
Description: 3 series of experiments for PGMA-PAMA-phenol with 7mm wells, comparing the base used and the voltage of the CA.
"""

from panda_lib import experiment_class, scheduler

PROJECT_ID = 20
EXPERIMENT_NAME = "PGMA-PAMA-phenol-base-voltage-screening"
CAMPAIGN_ID = 1
PLATE_TYPE = 4  # 7 mm diameter wells on ITO

voltages = [0.5, 1.0, 1.5]
bases = ["tea", "tpa", "teaa"]


def main():
    """Runs the PGMA-PAMA-phenol experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    for i in range(len(bases)):
        for voltage in voltages:
            experiments.append(
                experiment_class.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id="grobben_01_10",
                    well_id="A1",
                    well_type_number=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID + i,
                    solutions={
                        "PGMA-PAMA-phenol": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 1,
                        },
                        "TEA": {"volume": 320, "concentration": 1.0, "repeated": 1},
                        "TPA": {"volume": 320, "concentration": 1.0, "repeated": 1},
                        "TEAA": {"volume": 320, "concentration": 1.0, "repeated": 1},
                        "TBAP": {"volume": 320, "concentration": 1.0, "repeated": 1},
                        "DMF-TBAPrise": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 1,
                        },
                        "DMFrinse": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 1,
                        },
                        "ACNrinse": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 12,
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
                    cv_first_anodic_peak=1.0,
                    cv_second_anodic_peak=-0.6,
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
            if experiments[-1].project_campaign_id == 1:
                experiments[-1].solutions.pop("TPA")
                experiments[-1].solutions.pop("TEAA")
            elif experiments[-1].project_campaign_id == 2:
                experiments[-1].solutions.pop("TEA")
                experiments[-1].solutions.pop("TEAA")
            elif experiments[-1].project_campaign_id == 3:
                experiments[-1].solutions.pop("TEA")
                experiments[-1].solutions.pop("TPA")
            else:
                raise ValueError("Invalid campaign ID")

    scheduler.add_nonfile_experiments(experiments)
