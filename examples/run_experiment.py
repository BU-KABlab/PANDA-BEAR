#!/usr/bin/env python3
"""
Run a Single Experiment by ID

This script demonstrates how to run a specific experiment programmatically.

Usage:
    python examples/run_experiment.py --experiment-id 1
    python examples/run_experiment.py --experiment-id 1 --testing
"""

import argparse
import sys
from pathlib import Path

# Add src to path if running from repository
if Path(__file__).parent.parent.exists():
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from panda_lib.experiment_loop import experiment_loop_worker


def main():
    """Run a specific experiment by ID."""
    parser = argparse.ArgumentParser(
        description="Run a PANDA-BEAR experiment by ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run experiment 1 in testing mode (mock instruments)
  python examples/run_experiment.py --experiment-id 1 --testing

  # Run experiment 5 with real hardware
  python examples/run_experiment.py --experiment-id 5
        """,
    )

    parser.add_argument(
        "--experiment-id",
        type=int,
        required=True,
        help="ID of the experiment to run",
    )
    parser.add_argument(
        "--testing",
        action="store_true",
        help="Run in testing mode with mock instruments",
    )

    args = parser.parse_args()

    print(f"Running experiment {args.experiment_id}")
    if args.testing:
        print("Mode: Testing (mock instruments)")
    else:
        print("Mode: Production (real hardware)")

    try:
        experiment_loop_worker(
            use_mock_instruments=args.testing,
            one_off=True,  # Run one experiment and exit
            specific_experiment_id=args.experiment_id,
        )
        print(f"\n[OK] Experiment {args.experiment_id} completed successfully!")
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error running experiment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
