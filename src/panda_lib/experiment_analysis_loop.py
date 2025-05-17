"""
The analysis component is a process that monitors the experiments table for
records that have "needs_analysis" set to True. When it finds a record that
needs analysis, it will run the analysis on the experiment and update the
experiment record with the analysis results.
"""

import importlib.util
import logging
import os
import time
from multiprocessing import Queue
from pathlib import Path

from sqlalchemy import select

from panda_lib.sql_tools import Experiments
from panda_shared.db_setup import SessionLocal

logger = logging.getLogger("panda")


def analysis_worker(
    status_queue: Queue, process_id: int, generate_experiments: bool = False
):
    """
    Run the analysis process on experiments that are flagged for analysis.
    """
    breaking_issue: bool = False
    analyzers: dict = load_analyzers()
    status_queue.put((process_id, "started"))
    with SessionLocal() as connection:
        while True:
            # Get the experiments that need analysis
            status_queue.put((process_id, "checking for experiments"))
            experiments: list[Experiments] = connection.scalars(
                select(Experiments).filter(Experiments.needs_analysis == 1)
            )
            for experiment in experiments:
                # Find the analyzer that matches the project ID
                analyzer: callable = analyzers.get(experiment.analysis_id, None)
                if analyzer is None:
                    status_queue.put(
                        (
                            process_id,
                            f"error: no analyzer found for Analysis ID {experiment.analysis_id}",
                        )
                    )
                    continue  # Keep checking for other experiments

                # Run the analysis on the experiment
                try:
                    status_queue.put(
                        (
                            process_id,
                            f"analyzing experiment {experiment.experiment_id}",
                        )
                    )
                    output = analyzer(
                        experiment_id=experiment.experiment_id,
                        generate_experiment=generate_experiments,
                    )

                    # Unflag the experiment as needing analysis
                    experiment.needs_analysis = 0
                    connection.commit()

                    status_queue.put(
                        (
                            process_id,
                            f"analysis complete for experiment {experiment.experiment_id}. Output: {output}",
                        )
                    )
                except Exception as e:
                    status_queue.put(
                        (
                            process_id,
                            f"error: {e} on experiment {experiment.experiment_id}",
                        )
                    )
                    breaking_issue = True

            if breaking_issue:
                break
            status_queue.put((process_id, "idle"))
            time.sleep(5)

    status_queue.put((process_id, "finished"))
    return


def load_analyzers(
    directory: str = Path("panda_experiment_analyzers/").resolve(),
) -> dict[int, callable]:
    """
    Load the analysis scripts from the directory and return a dictionary
    of the analysis scripts.

    Args:
        directory: The directory to load the analysis scripts from.

    Returns:
        A dictionary of the analysis scripts.
    """
    analyzers = {}
    for analyzer in os.listdir(directory):
        if not analyzer.endswith(".py"):
            continue
        if analyzer == "__init__.py":
            continue
        file_path = directory / analyzer
        spec = importlib.util.spec_from_file_location(analyzer, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            script_id = module.ANALYSIS_ID
            analyzers[script_id] = module.main
        except (AttributeError, ModuleNotFoundError):
            logger.error("Error loading analyzer %s", analyzer)
    return analyzers
