"""
The analysis component is a process that monitors the experiments table for
records that have "needs_analysis" set to True. When it finds a record that
needs analysis, it will run the analysis on the experiment and update the
experiment record with the analysis results. The analysis process is
implemented as a class that is instantiated with a database connection and
a logger. The class has a run method that will run the analysis process.
"""

import importlib.util
import logging
import os
from multiprocessing import Queue
import time
from pathlib import Path

from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import Experiments

logger = logging.getLogger("panda")


def analysis_worker(
    status_queue: Queue, process_id: int, generate_experiments: bool = False
):
    """
    Run the analysis process on experiments that need analysis. The
    analysis process is run on the experiment and the results are stored
    in the experiment record in the database.
    """
    breaking_issue = False
    analyzers: dict = load_analyzers()
    status_queue.put((process_id, "started"))
    with SessionLocal() as connection:
        while True:
            # Get the experiments that need analysis
            status_queue.put((process_id, "checking for experiments"))
            experiments: list[Experiments] = (
                connection.query(Experiments)
                .filter(Experiments.needs_analysis == 1)
                .all()
            )
            for experiment in experiments:
                # Find the analyzer that matches the project ID
                # analyzer = next((a for a in analyzers if a.PROJECT_ID == experiment.project_id), None)
                analyzer = analyzers.get(experiment.analysis_id, None)
                if analyzer is None:
                    status_queue.put(
                        (
                            process_id,
                            f"error: no analyzer found for Anlysis ID {experiment.analysis_id}",
                        )
                    )
                    continue  # Keep checking for other experiments
                # Run the analysis on the experiment
                try:
                    status_queue.put(
                        (
                            process_id,
                            f"running analysis on experiment {experiment.experiment_id}",
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
) -> dict[int, object]:
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
