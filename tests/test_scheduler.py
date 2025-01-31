from sqlalchemy import text

from panda_lib.experiments import ExperimentBase
from panda_lib.scheduler import schedule_experiments
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    Experiments,
)
from shared_utilities.db_setup import SessionLocal

# @pytest.fixture(scope="module")
# def create_temp_database():
#     """
#     Creates an in-memory SQLite DB, sets up tables for tests.
#     """

#     # Verify we are using the in-memory database
#     if not engine.url.database == "temp.db":
#         # Stop the tests
#         raise Exception("Not using temp database")

#     try:
#         # populate the plate_types table
#         Base.metadata.create_all(bind=engine)
#         plate_types_data = [
#             (
#                 1,
#                 "gold",
#                 "grace bio-labs",
#                 96,
#                 "square",
#                 4,
#                 9,
#                 7,
#                 6,
#                 300,
#                 "ABCDEFGH",
#                 12,
#                 9,
#                 110,
#                 74,
#                 10.5,
#                 10.5,
#                 1,
#             ),
#             (
#                 2,
#                 "ito",
#                 "grace bio-labs",
#                 96,
#                 "square",
#                 4,
#                 9,
#                 7,
#                 6,
#                 300,
#                 "ABCDEFGH",
#                 12,
#                 9,
#                 110,
#                 74,
#                 10.5,
#                 10.5,
#                 1,
#             ),
#             (
#                 3,
#                 "gold",
#                 "pdms",
#                 96,
#                 "circular",
#                 3.25,
#                 8.9,
#                 6,
#                 4.5,
#                 150,
#                 "ABCDEFGH",
#                 12,
#                 8.9,
#                 110,
#                 74,
#                 10.5,
#                 10.5,
#                 1,
#             ),
#             (
#                 4,
#                 "ito",
#                 "pdms",
#                 96,
#                 "circular",
#                 3.25,
#                 9,
#                 6,
#                 4.5,
#                 150,
#                 "ABCDEFGH",
#                 12,
#                 9,
#                 110,
#                 74,
#                 5.5,
#                 5.5,
#                 1,
#             ),
#             (
#                 5,
#                 "plastic",
#                 "standard",
#                 96,
#                 "circular",
#                 3.48,
#                 9,
#                 10.9,
#                 8.5,
#                 500,
#                 "ABCDEFGH",
#                 12,
#                 9,
#                 110,
#                 74,
#                 10.5,
#                 10.5,
#                 1,
#             ),
#             (
#                 6,
#                 "pipette tip box",
#                 "standard",
#                 96,
#                 "circular",
#                 3.48,
#                 9,
#                 45,
#                 8.5,
#                 300000,
#                 "ABCDEFGH",
#                 12,
#                 9,
#                 110,
#                 74,
#                 10.5,
#                 10.5,
#                 1,
#             ),
#             (
#                 7,
#                 "gold",
#                 "pdms",
#                 50,
#                 "circular",
#                 5,
#                 13.5,
#                 6,
#                 4.5,
#                 350,
#                 "ABCDE",
#                 8,
#                 14,
#                 110,
#                 74,
#                 7.75,
#                 9,
#                 1,
#             ),
#         ]

#         with SessionLocal() as session:
#             session.execute(text("DELETE FROM panda_wellplate_types"))
#             session.commit()
#             for plate_type in plate_types_data:
#                 session.add(
#                     PlateTypes(
#                         id=plate_type[0],
#                         substrate=plate_type[1],
#                         gasket=plate_type[2],
#                         count=plate_type[3],
#                         shape=plate_type[4],
#                         radius_mm=plate_type[5],
#                         x_spacing=plate_type[6],
#                         gasket_height_mm=plate_type[7],
#                         max_liquid_height_mm=plate_type[8],
#                         capacity_ul=plate_type[9],
#                         rows=plate_type[10],
#                         cols=plate_type[11],
#                         y_spacing=plate_type[12],
#                         gasket_length_mm=plate_type[13],
#                         gasket_width_mm=plate_type[14],
#                         x_offset=plate_type[15],
#                         y_offset=plate_type[16],
#                         base_thickness=plate_type[17],
#                     )
#                 )

#             # Create db views
#             session.execute(
#                 text("""
#                 DROP VIEW IF EXISTS panda_queue;""")
#             )
#             session.execute(
#                 text("""
#                 CREATE VIEW panda_queue AS
#                 SELECT a.experiment_id,
#                 a.project_id,
#                 a.project_campaign_id,
#                 a.priority,
#                 a.process_type,
#                 a.filename,
#                 a.well_type AS [well type],
#                 c.well_id,
#                 c.status,
#                 c.status_date
#                 FROM panda_experiments AS a
#                 JOIN
#                 panda_wellplates AS b ON a.well_type = b.type_id
#                 JOIN
#                 panda_well_hx AS c ON a.experiment_id = c.experiment_id AND
#                             c.status IN ('queued', 'waiting')
#                 WHERE b.current = 1
#                 ORDER BY a.priority ASC,
#                     a.experiment_id ASC;
#                 """)
#             )

#             session.execute(
#                 text("""
#                 DROP VIEW IF EXISTS panda_well_status;""")
#             )
#             session.execute(
#                 text("""
#                 CREATE VIEW panda_well_status AS
#                 SELECT a.plate_id,
#                 b.type_id AS type_number,
#                 a.well_id,
#                 a.status,
#                 a.status_date,
#                 a.contents,
#                 a.experiment_id,
#                 a.project_id,
#                 a.volume,
#                 a.coordinates,
#                 c.capacity_ul AS capacity,
#                 c.gasket_height_mm AS height
#                 FROM panda_well_hx AS a
#                 JOIN
#                 panda_wellplates AS b ON a.plate_id = b.id
#                 JOIN
#                 panda_wellplate_types AS c ON b.type_id = c.id
#                 WHERE b.current = 1
#                 ORDER BY SUBSTRING(a.well_id, 1, 1),
#                     CAST(SUBSTRING(a.well_id, 2) AS UNSIGNED);
#                 """)
#             )

#             session.execute(
#                 text("""
#                 DROP VIEW IF EXISTS panda_vial_status;""")
#             )
#             session.execute(
#                 text("""
#                 CREATE VIEW panda_vial_status AS
#                 WITH RankedVials AS (
#                 SELECT v.*,
#                     ROW_NUMBER() OVER (PARTITION BY v.position ORDER BY v.updated DESC, v.id DESC) AS rn
#                 FROM panda_vials v
#                 WHERE v.active = 1
#                 )
#                 SELECT rv.*
#                 FROM RankedVials rv
#                 WHERE rv.rn = 1
#                 ORDER BY rv.position ASC;
#                 """)
#             )

#             session.execute(
#                 text("""
#                 DROP VIEW IF EXISTS panda_pipette_status;""")
#             )
#             session.execute(
#                 text("""
#                 CREATE VIEW panda_pipette_status AS
#                 SELECT *
#                 FROM panda_pipette
#                 WHERE id = (
#                     SELECT MAX(id)
#                     FROM panda_pipette
#                     )
#                 LIMIT 1;
#                 """)
#             )
#             session.commit()
#         # Add a wellplate of type 1, project 1, to the database
#         plate = Wellplate(
#             session_maker=SessionLocal,
#             plate_id=1,
#             create_new=True,
#             name="Test Plate",
#             type_id=1,
#             a1_x=0.0,
#             a1_y=0.0,
#             orientation=0,
#             rows="ABCDEFGH",
#             cols=12,
#         )
#         plate.activate_plate()

#         yield  # Allow tests to run

#     except Exception as e:
#         print(f"Error: {e}")
#         raise e

#     finally:
#         # Drop all tables
#         # Before dropping the tables, confirm we are using the in memory database
#         if engine.url.database == "temp.db":
#             # Drop all tables
#             Base.metadata.drop_all(bind=engine)
#             # Drop all views
#             with engine.connect() as connection:
#                 connection.execute(text("DROP VIEW IF EXISTS panda_queue;"))
#                 connection.execute(text("DROP VIEW IF EXISTS panda_well_status;"))
#                 connection.execute(text("DROP VIEW IF EXISTS panda_vial_status;"))
#                 connection.execute(text("DROP VIEW IF EXISTS panda_pipette_status;"))
#         else:
#             raise Exception("Not using in-memory database")


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
        plate_type_number=1,
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
        plate_type_number=1,
        protocol_id=1,
        analysis_id=1,
        pin="test_pin",
        experiment_type=1,
        jira_issue_key="test_key",
        priority=0,
        process_type=0,
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

    update_experiment_queue_priority(1, 1)
    experiment = SessionLocal().query(Experiments).filter_by(experiment_id=1).first()
    assert experiment.priority == 1


def test_update_experiment_info(temp_test_db):
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


def test_update_experiment_parameters(temp_test_db):
    """
    Tests updating the parameters of an experiment.
    """
    from panda_lib.scheduler import update_experiment_parameters

    experiment = ExperimentBase(
        experiment_id=6,
        project_id=1,
        project_campaign_id=1,
        plate_type_number=1,
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
    assert schedule_experiments([experiment]) == 1
    original_parameters = (
        SessionLocal()
        .query(ExperimentParameters)
        .filter_by(experiment_id=experiment.experiment_id)
        .all()
    )
    assert len(original_parameters) > 0
    original_solutions = (
        SessionLocal()
        .query(ExperimentParameters)
        .filter_by(experiment_id=experiment.experiment_id, parameter_name="solutions")
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
        .query(ExperimentParameters)
        .filter_by(experiment_id=experiment.experiment_id, parameter_name="solutions")
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
