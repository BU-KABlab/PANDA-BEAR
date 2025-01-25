import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.errors import OverDraftException, OverFillException
from panda_lib.labware.wellplate import (
    Well,
    Wellplate,
    load_configuration,
    save_configuration,
)
from panda_lib.sql_tools.panda_models import Base, PlateTypes, WellModel, Wellplates

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

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

with Session(engine) as session:
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


@pytest.fixture(scope="function")
def session():
    """Create a new database session for a test."""
    db = SessionLocal
    try:
        yield db
    finally:
        # db.close()
        pass


def test_create_new_well(session: sessionmaker):
    plate_type = 4

    well = Well(
        well_id="A1",
        plate_id=99,
        type_id=4,
        session_maker=session,
        create_new=True,
        name="Test Well",
    )

    with session() as db:
        plate_type_data = db.execute(
            select(PlateTypes).filter_by(id=plate_type)
        ).scalar_one()

        assert well.well_data.name == "Test Well"
        assert well.well_data.capacity == plate_type_data.capacity_ul
        assert well.well_data.volume == 0.0
        assert well.well_data.plate_id == 99
        assert well.well_data.height == plate_type_data.gasket_height_mm

        # Verify that the well in the db matches the well object
        db_well = db.execute(select(WellModel).filter_by(well_id="A1")).scalar_one()
        assert db_well.name == "Test Well"
        assert db_well.volume == well.well_data.volume
        assert db_well.capacity == well.well_data.capacity


def test_load_existing_well(session: sessionmaker):
    # Create a new well first
    well = Well(
        well_id="A1",
        session_maker=session,
        create_new=True,
        name="Test Well",
        plate_id=88,
        type_id=4,
    )

    # Load the existing well
    well = Well(well_id="A1", plate_id=88, session_maker=session, create_new=False)
    assert well.well_data.name == "Test Well"
    assert well.well_data.volume == 0.0


def test_add_contents(session: sessionmaker):
    well = Well(
        well_id="A1",
        session_maker=session,
        create_new=True,
        name="Test Well",
        volume=100.0,
        plate_id=77,
        type_id=4,
    )

    well.add_contents({"chemicalA": 50.0}, 50.0)
    assert well.well_data.volume == 150.0
    assert well.well_data.contents["chemicalA"] == 50.0


def test_add_contents_overfill(session: sessionmaker):
    well = Well(
        well_id="A1",
        session_maker=session,
        create_new=True,
        name="Test Well",
        volume=100.0,
        plate_id=66,
        type_id=4,
    )

    with pytest.raises(OverFillException):
        well.add_contents({"chemicalA": 100.0}, 100.0)


def test_remove_contents(session: sessionmaker):
    well = Well(
        well_id="A1",
        session_maker=session,
        create_new=True,
        name="Test Well",
        volume=100.0,
        contents={"chemicalA": 100.0},
        plate_id=55,
        type_id=4,
    )

    removed_contents = well.remove_contents(50.0)
    assert well.well_data.volume == 50.0
    assert removed_contents["chemicalA"] == 50.0


def test_remove_contents_overdraft(session: sessionmaker):
    well = Well(
        well_id="A1",
        session_maker=session,
        create_new=True,
        name="Test Well",
        volume=50.0,
        contents={"chemicalA": 50.0},
        plate_id=44,
        type_id=4,
    )

    with pytest.raises(OverDraftException):
        well.remove_contents(100.0)


def test_create_new_wellplate(session: sessionmaker):
    plate = Wellplate(
        session_maker=session,
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
    assert plate.plate_data.name == "Test Plate"
    assert plate.plate_data.type_id == 1

    # Verify that the plate in the db matches the plate object
    db_plate = (
        session()
        .execute(select(Wellplates).filter_by(id=plate.plate_data.id))
        .scalar_one()
    )
    assert db_plate.name == "Test Plate"
    assert db_plate.type_id == 1


def test_load_existing_wellplate(session: sessionmaker):
    # Create a new wellplate first
    Wellplate(
        session_maker=session,
        plate_id=2,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
    ).activate_plate()

    # Load the existing wellplate
    plate = Wellplate(session_maker=session, plate_id=2, create_new=False)
    assert plate.plate_data.name == "Test Plate"
    assert plate.plate_data.type_id == 1


def test_load_active_wellplate_by_default(session: sessionmaker):
    Wellplate(
        session_maker=session,
        plate_id=22,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
    ).activate_plate()

    plate = Wellplate(session_maker=session)
    assert plate.plate_data.name == "Test Plate"
    assert plate.plate_data.current is True
    assert plate.plate_data.id == 22


def test_recalculate_well_positions(session: sessionmaker):
    with open("tests/files/well_positions.json") as f:
        well_positions = json.load(f)

    plate = Wellplate(
        session_maker=session,
        plate_id=3,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
    )

    for orientation in range(4):
        plate.plate_data.orientation = orientation
        plate.recalculate_well_positions()
        expected_positions = well_positions[f"orientation_{orientation}"]

        for well_id, coords in expected_positions.items():
            assert plate.wells[well_id].well_data.coordinates["x"] == coords["x"]
            assert plate.wells[well_id].well_data.coordinates["y"] == coords["y"]


def test_activate_plate(session: sessionmaker):
    plate = Wellplate(
        session_maker=session,
        plate_id=4,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
        current=False,
    )
    plate.activate_plate()
    assert plate.plate_data.current is True


def test_deactivate_plate(session: sessionmaker):
    plate = Wellplate(
        session_maker=session,
        create_new=True,
        name="Test Plate",
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        rows="ABCDEFGH",
        cols=12,
        current=True,
        plate_id=9,
    )
    plate.deactivate_plate()
    assert plate.plate_data.current is False


def test_load_configuration():
    """Test loading the mill configuration from a JSON file. The Wellplate module uses this
    to determine the valid x and y coordinates for the wells."""
    config = load_configuration("tests/files/mill_config.json")
    assert float(config["$130"]) == 410.0
    assert float(config["$131"]) == 300.0


def test_save_configuration():
    """Test saving an updated configuration to a JSON file."""
    config = load_configuration("tests/files/mill_config.json")
    config["$130"] = 500.0
    config["$131"] = 400.0

    save_configuration(config, "tests/files/mill_config_updated.json")

    new_config = load_configuration("tests/files/mill_config_updated.json")
    assert float(new_config["$130"]) == 500.0
    assert float(new_config["$131"]) == 400.0

    Path("tests/files/mill_config_updated.json").unlink()  # Clean up the test file


if __name__ == "__main__":
    pytest.main()
