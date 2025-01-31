import os
import sys
from datetime import datetime

os.environ["TEMP_DB"] = "1"
import pytest  # noqa: E402

# Add the root directory of your project to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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
            ),
            (2, 200, 0.2, 0, 0, {}, datetime(2024, 12, 27, 1, 52, 35, 724000), 1, 0),
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
