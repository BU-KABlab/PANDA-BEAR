from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.hardware.panda_pipettes import (
    Pipette,
    PipetteModel,
    insert_new_pipette,
    select_current_pipette_id,
)
from panda_lib.sql_tools.panda_models import Base

# NOTE: The pipette has no check on volume, and may be overfilled

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

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
    (2, 200, 0.2, 0, 0, {}, datetime(2024, 12, 27, 1, 52, 35, 724000), 1, 0, 99),
]

with Session(engine) as session_maker:
    for pipette in pipette_data:
        session_maker.add(
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
    session_maker.commit()


@pytest.fixture(scope="function")
def session_maker():
    """Create a new database session for a test."""
    db = SessionLocal
    try:
        yield db
    finally:
        pass


def test_pipette_initialization(session_maker: sessionmaker):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    stmt = select(PipetteModel).where(PipetteModel.id == 2)
    pipette_db = session_maker().execute(stmt).scalars().first()
    assert pipette_db.capacity_ml == 0.2
    assert pipette_db.volume_ul == 0.0
    assert pipette_db.capacity_ul == 200.0
    assert pipette_db.volume_ml == 0.0
    assert pipette_db.contents == {}
    assert pipette_db.id == 2
    assert pipette_db.uses == 0
    assert pipette_db.panda_unit_id == 99

    # and assert that the pipette and pipette_db are the same
    assert pipette.capacity_ml == pipette_db.capacity_ml
    assert pipette.volume == pipette_db.volume_ul
    assert pipette.capacity_ul == pipette_db.capacity_ul
    assert pipette.volume_ml == pipette_db.volume_ml
    assert pipette.contents == pipette_db.contents
    assert pipette.id == pipette_db.id
    assert pipette.uses == pipette_db.uses
    assert pipette.panda_unit_id == pipette_db.panda_unit_id


def test_set_capacity(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.set_capacity(1000)
    assert pipette.capacity_ul == 1000.0
    assert pipette.capacity_ml == 1.0

    with pytest.raises(ValueError):
        pipette.set_capacity(-100)


def test_update_contents(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.update_contents("water", 500)
    assert pipette.contents["water"] == 500.0
    assert pipette.volume == 500.0

    pipette.update_contents("water", -200)
    assert pipette.contents["water"] == 300.0
    assert pipette.volume == 300.0


def test_volume_setter(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.volume = 1000
    assert pipette.volume == 1000.0

    with pytest.raises(ValueError):
        pipette.volume = -100


def test_volume_ml_setter(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.volume_ml = 1
    assert pipette.volume_ml == 1.0
    assert pipette.volume == 1000.0

    with pytest.raises(ValueError):
        pipette.volume_ml = -1


def test_reset_contents(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.update_contents("water", 500)
    pipette.reset_contents()
    assert pipette.contents == {}
    assert pipette.volume == 0.0
    assert pipette.volume_ml == 0.0


def test_liquid_volume(session_maker: Session):
    pipette: Pipette = Pipette(db_session_maker=session_maker)
    pipette.reset_contents()
    pipette.update_contents("water", 500)
    pipette.update_contents("ethanol", 300)
    assert pipette.liquid_volume() == 800.0


def test_invalid_pipette_id(session_maker: Session):
    with pytest.raises(ValueError):
        insert_new_pipette(session_maker=session_maker, pipette_id=-1)


def test_select_current_pipette_id(session_maker: Session):
    pipette_id = insert_new_pipette(session_maker=session_maker)
    current_pipette_id = select_current_pipette_id(session_maker=session_maker)
    assert current_pipette_id == pipette_id
