from sqlalchemy import select, text

from panda_lib.experiments import ExperimentBase
from panda_lib.scheduler import schedule_experiments
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    Experiments,
)
from shared_utilities.db_setup import SessionLocal


def test_schedule_experiments_no_experiments(temp_test_db):
    """
    Tests that scheduling with an empty list of experiments succeeds (returns zero).
    """

    result = schedule_experiments([])
    assert result == 0


def test_schedule_experiment_new_experiment(temp_test_db):
    """
    Tests scheduling a single new experiment with default conditions.
    """
    from panda_lib.scheduler import schedule_experiment

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        plate_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        experiment_type=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    result = schedule_experiment(experiment)
    assert result == 1


def test_schedule_experiment_existing_experiment(temp_test_db):
    """
    Tests scheduling an experiment that already exists in the database.
    """
    from panda_lib.scheduler import select_next_experiment_id

    exp_id = select_next_experiment_id()
    experiment = ExperimentBase(
        experiment_id=exp_id,
        project_id=1,
        project_campaign_id=1,
        plate_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    initial_result = schedule_experiments([experiment])
    assert initial_result == 1
    result = schedule_experiments([experiment])
    assert result == 0


def test_schedule_experiment_to_nonexistent_plate(temp_test_db):
    """
    Tests scheduling an experiment to a plate that doesn't exist.
    """
    from panda_lib.scheduler import schedule_experiment

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        plate_id=999,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    result = schedule_experiment(experiment)
    assert result == 0


def test_schedule_experiment_to_nonexistent_plate_type(temp_test_db):
    """
    Tests scheduling an experiment to a plate type that doesn't exist.
    """
    from panda_lib.scheduler import schedule_experiment

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        plate_id=1,
        wellplate_type_id=999,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    result = schedule_experiment(experiment)
    assert result == 0


def test_check_well_status(temp_test_db):
    """
    Tests checking the status of a well.
    """
    from panda_lib.scheduler import check_well_status

    well_status = check_well_status("D1")
    assert well_status == "new"


def test_choose_next_new_well(temp_test_db):
    """
    Tests choosing the next available well.
    """
    from panda_lib.scheduler import choose_next_new_well

    next_well = choose_next_new_well()
    assert next_well is not None


def test_change_well_status(temp_test_db):
    """
    Tests changing the status of a well.
    """
    from panda_lib.scheduler import check_well_status

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        well_type=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    # change_well_status("A1", experiment)
    experiment.set_status_and_save("running")

    well_status = check_well_status(experiment.well_id, experiment.plate_id)
    assert well_status == "running"


def test_read_next_experiment_from_queue(temp_test_db):
    """
    Tests reading the next experiment from the queue.
    """
    from panda_lib.scheduler import (
        read_next_experiment_from_queue,
    )

    # Add an experiment to the queue
    experiment = ExperimentBase(
        experiment_id=11,
        project_id=1,
        project_campaign_id=1,
        plate_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
    )
    result = schedule_experiments([experiment])
    assert result == 1
    experiment, filename = read_next_experiment_from_queue()
    assert experiment is not None
    assert filename == "test_file"


def test_update_experiment_queue_priority(temp_test_db):
    """
    Tests updating the priority of an experiment in the queue.
    """
    from panda_lib.scheduler import update_experiment_queue_priority

    experiment = ExperimentBase(
        experiment_id=154,
        project_id=1,
        project_campaign_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )

    schedule_experiments([experiment])
    update_experiment_queue_priority(experiment.experiment_id, 10)
    experiment = (
        SessionLocal().scalars(
            select(Experiments).filter_by(experiment_id=experiment.experiment_id)
        )
    ).first()

    assert experiment.priority == 10


def test_update_experiment_info(temp_test_db):
    """
    Tests updating the information of an experiment.
    """
    from panda_lib.scheduler import update_experiment_info

    experiment = ExperimentBase(
        experiment_id=111,
        project_id=1,
        project_campaign_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )

    schedule_experiments([experiment])
    experiment.priority = 1
    update_experiment_info(experiment, "priority")
    updated_experiment = (
        SessionLocal()
        .scalars(select(Experiments).where(Experiments.experiment_id == 111))
        .first()
    )

    assert updated_experiment.priority == 1


def test_update_experiment_parameters(temp_test_db):
    """
    Tests updating the parameters of an experiment.
    """
    from panda_lib.scheduler import update_experiment_parameters

    experiment = ExperimentBase(
        experiment_id=6,
        project_id=1,
        project_campaign_id=1,
        wellplate_type_id=1,
        protocol_name=1,
        analysis_id=1,
        priority=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    assert schedule_experiments([experiment]) == 1
    original_parameters = (
        SessionLocal()
        .scalars(
            select(ExperimentParameters).filter_by(
                experiment_id=experiment.experiment_id
            )
        )
        .all()
    )
    assert len(original_parameters) > 0
    original_solutions = (
        SessionLocal()
        .scalars(
            select(ExperimentParameters).filter_by(
                experiment_id=experiment.experiment_id, parameter_name="solutions"
            )
        )
        .first()
    )
    experiment.solutions = {
        "test": {
            "volume": 320,
            "concentration": 1.0,
            "repeated": 1,
        },
    }
    update_experiment_parameters(experiment, "solutions")
    updated_experiment = (
        SessionLocal()
        .scalars(
            select(ExperimentParameters).filter_by(
                experiment_id=experiment.experiment_id, parameter_name="solutions"
            )
        )
        .first()
    )
    assert updated_experiment.parameter_value != original_solutions.parameter_value


def test_check_project_id(temp_test_db):
    """
    Tests checking if a project ID exists in the projects table.
    """
    from panda_lib.scheduler import check_project_id

    # Get a list of all the projects
    with SessionLocal() as session:
        projects = session.execute(text("SELECT id FROM panda_projects")).fetchall()
        project_ids = [project[0] for project in projects]
    assert len(project_ids) > 0
    assert 1 in project_ids
    project_exists = check_project_id(1)
    assert project_exists is True


def test_add_project_id(temp_test_db):
    """
    Tests adding a project ID to the projects table.
    """
    from panda_lib.scheduler import add_project_id, check_project_id

    add_project_id(999)
    project_exists = check_project_id(999)
    assert project_exists is True


def test_determine_next_experiment_id(temp_test_db):
    """
    Tests determining the next experiment ID.
    """
    from panda_lib.scheduler import determine_next_experiment_id

    next_experiment_id = determine_next_experiment_id()
    assert isinstance(next_experiment_id, int)
    assert next_experiment_id > 0
