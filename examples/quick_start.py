#!/usr/bin/env python3
"""
Quick Start Example for PANDA-BEAR

This script demonstrates a minimal working example of running an experiment
programmatically without using the CLI menu.

Prerequisites:
1. Install PANDA-BEAR: pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git
2. Set up database: panda-db-setup
3. Configure .env file with PANDA_SDL_CONFIG_PATH
4. Create config.ini file (see config.ini.example)

Usage:
    python examples/quick_start.py
"""

import sys
from pathlib import Path

# Add src to path if running from repository
if Path(__file__).parent.parent.exists():
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase, ExperimentStatus
from panda_lib.experiment_loop import experiment_loop_worker


def main():
    """Run a simple test experiment."""
    print("PANDA-BEAR Quick Start Example")
    print("=" * 50)

    # Step 1: Create a simple experiment
    print("\n1. Creating experiment...")
    experiment_id = scheduler.determine_next_experiment_id()
    
    experiment = EchemExperimentBase(
        experiment_id=experiment_id,
        protocol_name="demo",  # Must exist in panda_experiment_protocols/
        well_id="A1",
        wellplate_type_id=4,  # Adjust to your wellplate type
        experiment_name="quick_start_test",
        project_id=1,
        project_campaign_id=1,
        solutions={
            # Add solutions that exist in your vials database
            # "solution_name": {"volume": 100, "concentration": 1.0, "repeated": 1}
        },
        # Minimal echem parameters
        ocp=0,
        baseline=0,
        cv=0,
        ca=0,  # Set to 1 if you want chronoamperometry
    )
    
    print(f"   Created experiment ID: {experiment_id}")

    # Step 2: Schedule the experiment
    print("\n2. Scheduling experiment...")
    scheduler.schedule_experiments([experiment])
    print("   Experiment scheduled successfully")

    # Step 3: Run the experiment (in testing mode with mock instruments)
    print("\n3. Running experiment in testing mode...")
    print("   (Using mock instruments - no hardware required)")
    print("   Press Ctrl+C to stop\n")
    
    try:
        experiment_loop_worker(
            use_mock_instruments=True,  # Use mocks for testing
            one_off=True,  # Run one experiment and exit
            specific_experiment_id=experiment_id,
        )
        print("\n[OK] Experiment completed successfully!")
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error running experiment: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure database is set up: panda-db-setup")
        print("2. Check config file exists and is valid")
        print("3. Verify protocol 'demo' exists in panda_experiment_protocols/")
        print("4. Check logs in logs_test/ directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
