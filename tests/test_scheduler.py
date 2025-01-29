import pytest
from sqlalchemy import text

from panda_lib.experiments import ExperimentBase
from panda_lib.labware.wellplates import Wellplate
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    Experiments,
    PlateTypes,
)


@pytest.fixture(scope="module")
def in_memory_db():
    """
    Creates an in-memory SQLite DB, sets up tables, and patches SessionLocal for tests.
    """

    # populate the plate_types table
    plate_types_data = [
        (
            1,
            "gold",
            "grace bio-labs",
            96,
            "square",
            4,
            9,
            7,
            6,
            300,
            "ABCDEFGH",
            12,
            9,
            110,
            74,
            10.5,
            10.5,
            1,
        ),
        (
            2,
            "ito",
            "grace bio-labs",
            96,
            "square",
            4,
            9,
            7,
            6,
            300,
            "ABCDEFGH",
            12,
            9,
            110,
            74,
            10.5,
            10.5,
            1,
        ),
        (
            3,
            "gold",
            "pdms",
            96,
            "circular",
            3.25,
            8.9,
            6,
            4.5,
            150,
            "ABCDEFGH",
            12,
            8.9,
            110,
            74,
            10.5,
            10.5,
            1,
        ),
        (
            4,
            "ito",
            "pdms",
            96,
            "circular",
            3.25,
            9,
            6,
            4.5,
            150,
            "ABCDEFGH",
            12,
            9,
            110,
            74,
            5.5,
            5.5,
            1,
        ),
        (
            5,
            "plastic",
            "standard",
            96,
            "circular",
            3.48,
            9,
            10.9,
            8.5,
            500,
            "ABCDEFGH",
            12,
            9,
            110,
            74,
            10.5,
            10.5,
            1,
        ),
        (
            6,
            "pipette tip box",
            "standard",
            96,
            "circular",
            3.48,
            9,
            45,
            8.5,
            300000,
            "ABCDEFGH",
            12,
            9,
            110,
            74,
            10.5,
            10.5,
            1,
        ),
        (
            7,
            "gold",
            "pdms",
            50,
            "circular",
            5,
            13.5,
            6,
            4.5,
            350,
            "ABCDE",
            8,
            14,
            110,
            74,
            7.75,
            9,
            1,
        ),
    ]

    with SessionLocal() as session:
        for plate_type in plate_types_data:
            session.add(
                PlateTypes(
                    id=plate_type[0],
                    substrate=plate_type[1],
                    gasket=plate_type[2],
                    count=plate_type[3],
                    shape=plate_type[4],
                    radius_mm=plate_type[5],
                    x_spacing=plate_type[6],
                    gasket_height_mm=plate_type[7],
                    max_liquid_height_mm=plate_type[8],
                    capacity_ul=plate_type[9],
                    rows=plate_type[10],
                    cols=plate_type[11],
                    y_spacing=plate_type[12],
                    gasket_length_mm=plate_type[13],
                    gasket_width_mm=plate_type[14],
                    x_offset=plate_type[15],
                    y_offset=plate_type[16],
                    base_thickness=plate_type[17],
                )
            )
        session.commit()
    # Add a wellplate of type 1, project 1, to the database
    Wellplate(
        session_maker=SessionLocal,
        plate_id=1,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
    )

    # Add a project 1 to the database

    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO panda_projects (id, project_name, added) VALUES (1, 'test_project', CURRENT_TIMESTAMP)"
            )
        )
        session.commit()


def test_schedule_experiments_no_experiments(in_memory_db):
    """
    Tests that scheduling with an empty list of experiments succeeds (returns zero).
    """
    from panda_lib.scheduler import schedule_experiments

    result = schedule_experiments([])
    assert result == 0


def test_schedule_experiment_new_experiment(in_memory_db):
    """
    Tests scheduling a single new experiment with default conditions.
    """
    from panda_lib.scheduler import schedule_experiment

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        well_type=1,
        protocol_id=1,
        analysis_id=1,
        pin="test_pin",
        experiment_type=1,
        jira_issue_key="test_key",
        priority=0,
        process_type=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    result = schedule_experiment(experiment)
    assert result == 1


def test_check_well_status(in_memory_db):
    """
    Tests checking the status of a well.
    """
    from panda_lib.scheduler import check_well_status

    well_status = check_well_status("A1")
    assert well_status == "new"


def test_choose_next_new_well(in_memory_db):
    """
    Tests choosing the next available well.
    """
    from panda_lib.scheduler import choose_next_new_well

    next_well = choose_next_new_well()
    assert next_well == "A1"


def test_change_well_status(in_memory_db):
    """
    Tests changing the status of a well.
    """
    from panda_lib.scheduler import change_well_status, check_well_status

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        well_type=1,
        protocol_id=1,
        analysis_id=1,
        pin="test_pin",
        experiment_type=1,
        jira_issue_key="test_key",
        priority=0,
        process_type=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    change_well_status("A1", experiment)
    well_status = check_well_status("A1")
    assert well_status == "running"


def test_read_next_experiment_from_queue(in_memory_db):
    """
    Tests reading the next experiment from the queue.
    """
    from panda_lib.scheduler import read_next_experiment_from_queue

    experiment, filename = read_next_experiment_from_queue()
    assert experiment is not None
    assert filename == "test_file"


def test_update_experiment_queue_priority(in_memory_db):
    """
    Tests updating the priority of an experiment in the queue.
    """
    from panda_lib.scheduler import update_experiment_queue_priority

    update_experiment_queue_priority(1, 1)
    experiment = SessionLocal().query(Experiments).filter_by(experiment_id=1).first()
    assert experiment.priority == 1


def test_update_experiment_info(in_memory_db):
    """
    Tests updating the information of an experiment.
    """
    from panda_lib.scheduler import update_experiment_info

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        well_type=1,
        protocol_id=1,
        analysis_id=1,
        pin="test_pin",
        experiment_type=1,
        jira_issue_key="test_key",
        priority=0,
        process_type=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )

    update_experiment_info(experiment, "priority")
    updated_experiment = (
        SessionLocal().query(Experiments).filter_by(experiment_id=1).first()
    )
    assert updated_experiment.priority == 0


def test_update_experiment_parameters(in_memory_db):
    """
    Tests updating the parameters of an experiment.
    """
    from panda_lib.scheduler import update_experiment_parameters

    experiment = ExperimentBase(
        experiment_id=1,
        project_id=1,
        project_campaign_id=1,
        well_type=1,
        protocol_id=1,
        analysis_id=1,
        pin="test_pin",
        experiment_type=1,
        jira_issue_key="test_key",
        priority=0,
        process_type=0,
        filename="test_file",
        needs_analysis=False,
        created="2022-01-01T00:00:00Z",
        updated="2022-01-01T00:00:00Z",
    )
    update_experiment_parameters(experiment, "priority")
    updated_experiment = (
        SessionLocal().query(ExperimentParameters).filter_by(experiment_id=1).first()
    )
    assert updated_experiment.priority == 0


def test_check_project_id(in_memory_db):
    """
    Tests checking if a project ID exists in the projects table.
    """
    from panda_lib.scheduler import check_project_id

    project_exists = check_project_id(1)
    assert project_exists is False


def test_add_project_id(in_memory_db):
    """
    Tests adding a project ID to the projects table.
    """
    from panda_lib.scheduler import add_project_id, check_project_id

    add_project_id(999)
    project_exists = check_project_id(999)
    assert project_exists is True


def test_determine_next_experiment_id(in_memory_db):
    """
    Tests determining the next experiment ID.
    """
    from panda_lib.scheduler import determine_next_experiment_id

    next_experiment_id = determine_next_experiment_id()
    assert next_experiment_id == 10000000
