"""
Simple electrode validation script for PANDA-BEAR
This script connects to the eMStat potentiostat, performs OCP measurements,
and saves the data to validate electrode functionality.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from panda_lib.actions.electrochemistry import open_circuit_potential
from panda_lib.experiments.experiment_types import (
    EchemExperimentBase,
    ExperimentResults,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("electrode_validation")

# Configuration
DRY_RUN = False  # Set to True to run without actual hardware
DATA_DIR = Path("./data")  # Simple data directory

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
experiment_dir = DATA_DIR / f"electrode_validation_{timestamp}"
os.makedirs(experiment_dir, exist_ok=True)


def create_simple_experiment():
    """Create a simple experiment for electrode validation"""
    # Create an experiment with default parameters for OCP
    experiment = EchemExperimentBase(
        experiment_id=f"electrode_validation_{timestamp}",
        experiment_name="Electrode Validation",
        well_id="TEST",
        project_id=0,
        project_campaign_id=0,
        baseline=0,
        # OCP parameters
        ocp_time=10.0,  # 10 seconds of OCP measurement
        ocp_sample_period=0.1,
        # Required placeholder values
        ca_prestep_voltage=0.0,
        ca_prestep_time_delay=0.0,
        ca_step_1_voltage=0.0,
        ca_step_1_time=0.0,
        ca_step_2_voltage=0.0,
        ca_step_2_time=0.0,
        ca_sample_period=0.1,
        cv_initial_voltage=0.0,
        cv_first_anodic_peak=1.0,
        cv_second_anodic_peak=-0.5,
        cv_final_voltage=0.0,
        cv_scan_rate_cycle_1=0.1,
        cv_scan_rate_cycle_2=0.1,
        cv_scan_rate_cycle_3=0.1,
        cv_cycle_count=3,
    )
    # Create results object for the experiment
    experiment.results = ExperimentResults(experiment_id=experiment.experiment_id)
    return experiment


def run_ocp_test(experiment):
    """Run OCP test with the given experiment"""
    logger.info("Starting Open Circuit Potential (OCP) measurement")

    try:
        # Run OCP measurement
        ocp_passed, ocp_voltage = open_circuit_potential(
            file_tag="validation", exp=experiment, testing=DRY_RUN
        )

        logger.info(
            f"OCP Test completed: Passed = {ocp_passed}, Voltage = {ocp_voltage:.4f}V"
        )

        # Check if OCP file was created and exists
        if experiment.results.ocp_file and os.path.exists(experiment.results.ocp_file):
            logger.info(f"OCP data saved to: {experiment.results.ocp_file}")

            try:
                # Load and analyze OCP data
                ocp_data = pd.read_csv(
                    experiment.results.ocp_file,
                    sep=" ",
                    header=None,
                    names=[
                        "Time",
                        "Vf",
                        "Vu",
                        "Vsig",
                        "Ach",
                        "Overload",
                        "StopTest",
                        "Temp",
                    ],
                )
                logger.info(f"OCP data points: {len(ocp_data)}")
                logger.info(
                    f"OCP voltage range: {ocp_data['Vf'].min():.4f}V to {ocp_data['Vf'].max():.4f}V"
                )

                # Create a simple plot of the OCP data
                plt.figure(figsize=(10, 6))
                plt.plot(ocp_data["Time"], ocp_data["Vf"])
                plt.xlabel("Time (s)")
                plt.ylabel("Voltage (V)")
                plt.title("Open Circuit Potential Measurement")
                plt.grid(True)
                plot_path = experiment_dir / "ocp_plot.png"
                plt.savefig(plot_path)
                logger.info(f"OCP plot saved to: {plot_path}")

            except Exception as e:
                logger.error(f"Error analyzing OCP data: {e}")

        return ocp_passed, ocp_voltage

    except Exception as e:
        logger.error(f"Error during OCP measurement: {e}")
        return False, 0.0


def main():
    """Main function to run electrode validation"""
    logger.info("Starting electrode validation")

    try:
        # Prompt user to confirm electrode is connected
        input(
            "Please ensure the electrode is properly connected to the eMStat potentiostat and press Enter to continue..."
        )

        # Create a simple experiment
        experiment = create_simple_experiment()

        # Run OCP test
        ocp_passed, ocp_voltage = run_ocp_test(experiment)

        # Evaluate results
        if ocp_passed:
            logger.info("[PASS] Electrode validation PASSED!")
            logger.info(f"OCP voltage: {ocp_voltage:.4f}V")
            if -0.5 < ocp_voltage < 0.5:
                logger.info("[PASS] OCP voltage is within expected range (-0.5V to 0.5V)")
            else:
                logger.warning(
                    "[WARNING] OCP voltage is outside expected range (-0.5V to 0.5V)"
                )
        else:
            logger.error("[FAIL] Electrode validation FAILED!")
            logger.error(f"OCP voltage: {ocp_voltage:.4f}V")

    except Exception as e:
        logger.error(f"Error during electrode validation: {e}")

    finally:
        logger.info("Electrode validation complete")

        # Save a simple summary report
        try:
            summary_path = experiment_dir / "validation_summary.txt"
            with open(summary_path, "w") as f:
                f.write("Electrode Validation Summary\n")
                f.write("===========================\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if "ocp_passed" in locals():
                    f.write(f"OCP Test Passed: {ocp_passed}\n")
                    f.write(f"OCP Voltage: {ocp_voltage:.4f}V\n")
                if (
                    "experiment" in locals()
                    and hasattr(experiment, "results")
                    and experiment.results.ocp_file
                ):
                    f.write(f"OCP Data File: {experiment.results.ocp_file}\n")
                f.write("\n")
            logger.info(f"Summary report saved to: {summary_path}")
        except Exception as e:
            logger.error(f"Error saving summary report: {e}")


if __name__ == "__main__":
    main()
