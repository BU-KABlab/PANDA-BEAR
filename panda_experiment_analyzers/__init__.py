"""
The analysis component is a process that monitors the experiments table for
records that have "needs_analysis" set to True. When it finds a record that
needs analysis, it will run the analysis on the experiment and update the
experiment record with the analysis results. The analysis process is
implemented as a class that is instantiated with a database connection and
a logger. The class has a run method that will run the analysis process.
"""
import logging
from multiprocessing import Queue
import time

from panda_experiment_analyzers.example_analyzer import \
    Analyzer as example_analysis
from panda_experiment_analyzers.pedot import Analyzer as pedot_analysis
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import Experiments

logger = logging.getLogger("panda")

def analysis_worker(status_queue: Queue, process_id: int, generate_experiments: bool = False):
    """
    Run the analysis process on experiments that need analysis. The
    analysis process is run on the experiment and the results are stored
    in the experiment record in the database.
    """
    breaking_issue = False
    analyzers:list[example_analysis] = [example_analysis(), pedot_analysis()]
    status_queue.put((process_id,"started"))
    with SessionLocal() as connection:
        while True:
            # Get the experiments that need analysis
            status_queue.put((process_id,"checking for experiments"))
            experiments:list[Experiments] = connection.query(Experiments).filter(Experiments.needs_analysis == 1).all()
            for experiment in experiments:
                # Find the analyzer that matches the project ID
                analyzer = next((a for a in analyzers if a.PROJECT_ID == experiment.project_id), None)
                if analyzer is None:
                    status_queue.put((process_id,f"error: no analyzer found for project {experiment.project_id}"))
                    breaking_issue = True
                # Run the analysis on the experiment
                try:
                    status_queue.put((process_id,f"running analysis on experiment {experiment.experiment_id}"))
                    _ = analyzer.main(experiment_id = experiment.experiment_id, generate_experiment = generate_experiments)

                    # Unflag the experiment as needing analysis
                    connection.query(Experiments).filter(Experiments.experiment_id == experiment.experiment_id).update(
                        {"needs_analysis": False}
                    )
                    connection.commit()
                    status_queue.put((process_id,f"analysis complete for experiment {experiment.experiment_id}"))
                except Exception as e:
                    status_queue.put((process_id,f"error: {e} on experiment {experiment.experiment_id}"))
                    breaking_issue = True
            if breaking_issue:
                break
            time.sleep(5)
                
    status_queue.put((process_id,"finished"))
    return

