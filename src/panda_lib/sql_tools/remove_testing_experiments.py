"""Clean out testing experiments"""

# from panda_lib.sql_tools.sql_utilities import (
#     execute_sql_command,
#     execute_sql_command_no_return,
# )
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    ExperimentResults,
    Experiments,
    WellModel,
)
from shared_utilities.db_setup import SessionLocal


def main():
    """
    For this script we will do the following:
    Go to the experiments table and find experiment_ids with project_id = 999
    Using this list of experiment_ids we will delete records from the following tables:
    - experiment_parameters
    - experiment_results
    For well_hx we can use the project_id again and we will update instead of delete:
    - experiment_id to NULL
    - project_id to NULL
    - status to 'new'
    - status_date to NULL
    - contents to {}
    - volume to 0
    Finally remove the experiments from experiments table
    Get the experiment_ids
    """

    with SessionLocal() as session:
        experiment_ids = (
            session.query(Experiments.experiment_id)
            .filter(Experiments.project_id == 999)
            .all()
        )

        experiment_ids = [experiment_id[0] for experiment_id in experiment_ids]

        session.query(ExperimentParameters).filter(
            ExperimentParameters.experiment_id.in_(experiment_ids)
        ).delete(synchronize_session=False)
        session.query(ExperimentResults).filter(
            ExperimentResults.experiment_id.in_(experiment_ids)
        ).delete(synchronize_session=False)
        session.query(WellModel).filter(WellModel.project_id == 999).update(
            {
                WellModel.experiment_id: None,
                WellModel.project_id: None,
                WellModel.status: "new",
                WellModel.status_date: None,
                WellModel.contents: {},
                WellModel.volume: 0,
            },
            synchronize_session=False,
        )
        session.query(Experiments).filter(Experiments.project_id == 999).delete(
            synchronize_session=False
        )
        session.commit()

    print("Testing experiments removed")


if __name__ == "__main__":
    main()
