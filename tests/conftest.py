import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock

import pytest

os.environ["TEMP_DB"] = "1"

# Add the root directory of your project to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def testing_config_file():
    """
    Creates a temporary testing config file for tests.
    This separates testing configuration from the local environment.
    """
    # Store original environment variables to restore later
    original_env = {}
    env_vars_to_store = [
        "PANDA_SDL_CONFIG_PATH",
        "TEMP_DB",
        "PANDA_UNIT_ID",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
    ]

    for var in env_vars_to_store:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create a temporary config file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)

    # Clear any existing configuration cache
    try:
        from shared_utilities.config.config_tools import read_config, reload_config

        # Clear the LRU cache for read_config to force reconfiguration
        read_config.cache_clear()
        # Explicitly reload config if needed
        reload_config()
    except (ImportError, AttributeError) as e:
        print(f"Warning: Failed to clear config cache: {e}")

    # Write default testing configuration
    with open(temp_path, "w") as f:
        f.write("""
[PANDA]
version = 2.0
unit_id = 99
unit_name = "Buster"

[DEFAULTS]
air_gap = 40.0
drip_stop_volume = 5.0
pipette_purge_volume = 20.0
pumping_rate = 0.3

[OPTIONS]
testing = True
random_experiment_selection = False
use_slack = False
use_obs = False
precision = 6

[LOGGING]
file_level = DEBUG
console_level = ERROR

[GENERAL]
local_dir = panda_lib
protocols_dir = panda_experiment_protocols
generators_dir = panda_experiment_generators

[TESTING]
testing_dir = panda_lib
testing_db_type = sqlite
testing_db_address = test_db.db
testing_db_user = None
testing_db_password = None
logging_dir = logs_test
data_dir = data_test

[PRODUCTION]
production_dir = 
production_db_type = 
production_db_address = 
production_db_password = 
logging_dir =
data_dir =

[OBS]
obs_host = localhost
obs_password = 
obs_port = 4455
obs_timeout = 3

[SLACK]
slack_token = 
slack_conversation_channel_id = 
slack_alert_channel_id = 
slack_data_channel_id = 
slack_test_conversation_channel_id = 
slack_test_alert_channel_id = 
slack_test_data_channel_id = 

[MILL]
port = COM4
baudrate = 115200
timeout = 10
config_file = mill_config.json

[PUMP]
port = 
baudrate = 19200
timeout = 10
syringe_inside_diameter = 4.600
syringe_capacity = 1
max_pumping_rate = 0.654
units = MM

[SCALE]
port = 
baudrate = 9600
timeout = 10

[CAMERA]
camera_type = 
webcam_id = 0
webcam_resolution_width = 1280
webcam_resolution_height = 720

[ARDUINO]
port = COM3
baudrate = 115200
timeout = 10

[TOOLS]
offsets = [
	{
	"name": "center",
	"x": 0.0,
	"y": 0.0,
	"z": 0.0
	},
	{
	"name": "pipette",
	"x": -99.0,
	"y": 0.0,
	"z": 130.0
	},
	{
	"name": "electrode",
	"x": 22.0,
	"y": 51.0,
	"z": 124.0
	},
	{
	"name": "decapper",
	"x": -73.0,
	"y": 0.0,
	"z": 72.0
	},
	{
	"name": "lens",
	"x": 4.0,
	"y": -1.0,
	"z": 0.0
	}
	]


""")

    # Set environment variables for testing
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_UNIT_ID"] = "99"  # Set unit ID to match config file
    os.environ["TEMP_DB"] = "1"  # Ensure we're using temp DB

    # Force config_tools to use our test config
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path

    print(f"Test config created at: {temp_path}")
    print(f"Environment set: PANDA_UNIT_ID={os.environ.get('PANDA_UNIT_ID')}")

    # Let the tests run
    yield temp_path

    # Clean up after tests
    try:
        os.unlink(temp_path)

        # Restore original environment variables
        for var in env_vars_to_store:
            if var in original_env:
                os.environ[var] = original_env[var]
            elif var in os.environ:
                del os.environ[var]

        print("Test environment cleaned up and original environment restored")
    except (OSError, KeyError) as e:
        print(f"Error during cleanup: {e}")


@pytest.fixture(scope="session")
def temp_test_db():
    """
    Creates an temp SQLite DB, sets up tables for tests.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import close_all_sessions, sessionmaker

    from hardware.panda_pipette import (
        PipetteModel,
    )
    from panda_lib.labware.schemas import VialWriteModel, WellWriteModel
    from panda_lib.labware.wellplates import Wellplate
    from panda_lib.sql_tools.panda_models import (
        Base,
        PlateTypes,
        Vials,
        WellModel,
    )
    # Toggle using the temp db in the config

    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///temp.db", echo=False)
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Patch the SessionLocal globally
    global SessionLocal
    SessionLocal = TestingSessionLocal

    # Verify we are using the in-memory database
    if engine.url.database != "temp.db":
        raise Exception("Not using temp database")

    try:
        # Populate the plate_types table
        Base.metadata.create_all(bind=engine)
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
            session.execute(text("DELETE FROM panda_wellplate_types"))
            session.commit()
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

            # Create db views
            views = [
                "DROP VIEW IF EXISTS panda_queue;",
                """
                CREATE VIEW panda_queue AS
                SELECT a.experiment_id, a.project_id, a.project_campaign_id, a.priority, a.process_type, a.filename,
                       a.well_type, c.well_id, c.status, c.status_date
                FROM panda_experiments AS a
                JOIN panda_wellplates AS b ON a.well_type = b.type_id
                JOIN panda_well_hx AS c ON a.experiment_id = c.experiment_id AND c.status IN ('queued', 'waiting')
                WHERE b.current = 1
                ORDER BY a.priority ASC, a.experiment_id ASC;
                """,
                "DROP VIEW IF EXISTS panda_well_status;",
                """
                CREATE VIEW panda_well_status AS
                SELECT a.plate_id, b.type_id AS type_number, a.well_id, a.status, a.status_date, a.contents, a.experiment_id,
                       a.project_id, a.volume, a.coordinates, c.capacity_ul AS capacity, c.gasket_height_mm AS height
                FROM panda_well_hx AS a
                JOIN panda_wellplates AS b ON a.plate_id = b.id
                JOIN panda_wellplate_types AS c ON b.type_id = c.id
                WHERE b.current = 1
                ORDER BY SUBSTRING(a.well_id, 1, 1), CAST(SUBSTRING(a.well_id, 2) AS UNSIGNED);
                """,
                "DROP VIEW IF EXISTS panda_vial_status;",
                """
                CREATE VIEW panda_vial_status AS
                WITH RankedVials AS (
                    SELECT v.*, ROW_NUMBER() OVER (PARTITION BY v.position ORDER BY v.updated DESC, v.id DESC) AS rn
                    FROM panda_vials v
                    WHERE v.active = 1
                )
                SELECT rv.*
                FROM RankedVials rv
                WHERE rv.rn = 1
                ORDER BY rv.position ASC;
                """,
                "DROP VIEW IF EXISTS panda_pipette_status;",
                """
                CREATE VIEW panda_pipette_status AS
                SELECT *
                FROM panda_pipette
                WHERE id = (SELECT MAX(id) FROM panda_pipette)
                LIMIT 1;
                """,
            ]

            for view in views:
                session.execute(text(view))
            session.commit()

        # populate the panda_pipette table with a few pipettes
        pipette_data = [
            (
                1,
                200,
                0.2,
                0,
                0,
                {"edot": 0.0, "rinse": 0.0, "liclo4": 0.0},
                datetime(2024, 12, 27, 1, 52, 35, 723000),
                0,
                159,
                99,
            ),
            (
                2,
                200,
                0.2,
                0,
                0,
                {},
                datetime(2024, 12, 27, 1, 52, 35, 724000),
                1,
                0,
                99,
            ),
        ]

        with SessionLocal() as sesh:
            for pipette in pipette_data:
                sesh.add(
                    PipetteModel(
                        id=pipette[0],
                        capacity_ul=pipette[1],
                        capacity_ml=pipette[2],
                        volume_ul=pipette[3],
                        volume_ml=pipette[4],
                        contents=pipette[5],
                        updated=pipette[6],
                        active=pipette[7],
                        uses=pipette[8],
                        panda_unit_id=pipette[9],
                    )
                )
            sesh.commit()

        # Add a wellplate of type 1, type 1, to the database
        plate = Wellplate(
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
            panda_unit_id=99,
        )
        plate.activate_plate()

        with SessionLocal() as sesh:
            vials = [
                VialWriteModel(
                    position="s2",
                    category=0,
                    name="edot",
                    contents={"edot": 20000},
                    viscosity_cp=1,
                    concentration=0.01,
                    density=1,
                    height=57,
                    radius=14,
                    volume=20000,
                    capacity=20000,
                    contamination=0,
                    coordinates={"x": -4, "y": -106, "z": -83},
                    base_thickness=1,
                    dead_volume=1000,
                    panda_unit_id=99,
                ),
                VialWriteModel(
                    position="s1",
                    category=0,
                    name="solution1",
                    contents={"solution1": 20000},
                    viscosity_cp=1,
                    concentration=0.01,
                    density=1,
                    height=57,
                    radius=14,
                    volume=20000,
                    capacity=20000,
                    contamination=0,
                    coordinates={"x": -4, "y": -136, "z": -83},
                    base_thickness=1,
                    dead_volume=1000,
                    panda_unit_id=99,
                ),
                VialWriteModel(
                    position="w0",
                    category=1,
                    name="waste",
                    contents={},
                    viscosity_cp=1,
                    concentration=0.0,
                    density=1,
                    height=57,
                    radius=14,
                    volume=0,
                    capacity=20000,
                    contamination=0,
                    coordinates={"x": -4, "y": -106, "z": -83},
                    base_thickness=1,
                    dead_volume=1000,
                    panda_unit_id=99,
                ),
                VialWriteModel(
                    position="s3",
                    category=0,
                    name="test_solution",
                    contents={"test_solution": 20000},
                    viscosity_cp=1,
                    concentration=0.01,
                    density=1,
                    height=57,
                    radius=14,
                    volume=20000,
                    capacity=20000,
                    contamination=0,
                    coordinates={"x": -4, "y": -166, "z": -83},
                    base_thickness=1,
                    dead_volume=1000,
                    panda_unit_id=99,
                ),
            ]

            for vial in vials:
                sesh.add(Vials(**vial.model_dump()))

            well = WellWriteModel(
                plate_id=123,
                well_id="B5",
                experiment_id=0,
                project_id=0,
                status="new",
                contents={},
                volume=0,
                coordinates={"x": -231.0, "y": -42.0, "z": -71.0},
                base_thickness=1,
                height=6,
                radius=3.25,
                capacity=150,
                contamination=0,
                dead_volume=0,
                name="123_B5",
            )
            sesh.add(WellModel(**well.model_dump()))
            sesh.commit()

        yield  # Allow tests to run

    except Exception as e:
        print(f"Error: {e}")
        raise e

    finally:
        # Drop all tables and views
        if engine.url.database == "temp.db":
            Base.metadata.drop_all(bind=engine)
            with engine.connect() as connection:
                views = [
                    "panda_queue",
                    "panda_well_status",
                    "panda_vial_status",
                    "panda_pipette_status",
                ]
                for view in views:
                    connection.execute(text(f"DROP VIEW IF EXISTS {view};"))
        else:
            raise Exception("Not using in-memory database")

        # Toggle using the temp db in the config
        os.environ["TEMP_DB"] = "0"

        close_all_sessions()
        engine.dispose()
        SessionLocal = None
        del SessionLocal

        # Ensure all connections are closed before deleting the file
        import time

        # Wait a moment for connections to close
        time.sleep(1)
        try:
            os.remove("temp.db")
        except PermissionError:
            print("Failed to delete temp.db, file is in use.")


@pytest.fixture
def mock_config():
    """Mock configuration settings."""
    config_mock = MagicMock()
    config_mock.getfloat.return_value = 0.5
    config_mock.get.return_value = "test_path"
    return config_mock


@pytest.fixture
def mock_gamry_potentiostat():
    """Mock for the Gamry Potentiostat."""
    mock = MagicMock()

    # Mock common method returns
    mock.pstatconnect.return_value = True
    mock.pstatdisconnect.return_value = True
    mock.setfilename.return_value = "test_filename"
    mock.OCP.return_value = True
    mock.activecheck.return_value = True
    mock.check_vf_range.return_value = (True, -0.5)  # Success, voltage value
    mock.chrono.return_value = True
    mock.cyclic.return_value = True

    return mock


@pytest.fixture
def mock_chrono_parameters():
    """Mock for chronoamperometry parameters."""
    return MagicMock()


@pytest.fixture
def mock_cv_parameters():
    """Mock for CV parameters."""
    return MagicMock()


@pytest.fixture
def mock_ocp_parameters():
    """Mock for OCP parameters."""
    return MagicMock()


@pytest.fixture
def mock_toolkit():
    """Mock for the Toolkit."""
    mock = MagicMock()
    mock.mill.safe_move.return_value = True
    mock.wellplate.echem_height = 10.0
    return mock


@pytest.fixture
def mock_well():
    """Mock for a Well."""
    mock = MagicMock()
    mock.top_coordinates = [10.0, 20.0, 30.0]
    return mock


@pytest.fixture
def mock_experiment():
    """Mock for an EchemExperimentBase."""
    mock = MagicMock()
    mock.experiment_id = "test_experiment"
    mock.project_id = "test_project"
    mock.project_campaign_id = "test_campaign"
    mock.well_id = "test_well"
    mock.results.set_ocp_file.return_value = None
    mock.results.set_ocp_ca_file.return_value = None
    mock.results.set_ca_data_file.return_value = None
    mock.results.set_ocp_cv_file.return_value = None
    mock.results.set_cv_data_file.return_value = None
    mock.set_status_and_save.return_value = None
    mock.baseline = 0
    mock.ca_prestep_voltage = -0.1
    mock.ca_prestep_time_delay = 5
    mock.ca_step_1_voltage = -0.5
    mock.ca_step_1_time = 300
    mock.ca_step_2_voltage = 0.0
    mock.ca_step_2_time = 0
    mock.ca_sample_period = 0.5
    mock.cv_initial_voltage = -0.5
    mock.cv_first_anodic_peak = 0.8
    mock.cv_second_anodic_peak = 0.0
    mock.cv_final_voltage = -0.5
    mock.cv_scan_rate_cycle_1 = 0.1
    mock.cv_scan_rate_cycle_2 = 0.0
    mock.cv_scan_rate_cycle_3 = 0.0
    mock.cv_cycle_count = 1
    mock.well = "test_well"
    return mock
