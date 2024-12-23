import pytest

# from sqlalchemy import create_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.sql_tools.panda_models import Base, Vials
from panda_lib.vials_v2 import (
    Vial,
    delete_vial_position_from_db,
    get_active_vials,
    read_vials,
    reset_vials,
)

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Create the tables in the in-memory database
Base.metadata.create_all(engine)


@pytest.fixture(scope="function")
def session():
    """Create a new database session for a test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_new_vial(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        session=session,
    )
    db_vial = session.query(Vials).filter_by(position="A1").one()
    assert db_vial.name == "Test Vial"
    assert db_vial.volume == 100.0


def test_update_vial(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        session=session,
    )

    vial.volume = 150.0

    db_vial = session.query(Vials).filter_by(position="A1").one()
    assert db_vial.volume == 150.0


def test_fetch_vial_from_db(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
    )

    fetched_vial = Vial(position="A1", category=0, create_new=False)
    assert fetched_vial.name == "Test Vial"
    assert fetched_vial.volume == 100.0


def test_delete_vial(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        session=session,
    )

    delete_vial_position_from_db("A1")
    db_vial = session.query(Vials).filter_by(position="A1").one_or_none()
    assert db_vial is None


def test_reset_vial(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        session=session,
    )

    vial.reset_vial()
    assert vial.volume == 200.0
    assert vial.contamination == 0


def test_add_contents(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        session=session,
    )

    vial.add_contents({"chemicalA": 50.0}, 50.0)
    assert vial.volume == 150.0
    assert vial.contents["chemicalA"] == 50.0


def test_remove_contents(session: Session):
    vial = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        contents={"chemicalA": 100.0},
        session=session,
    )

    removed_contents = vial.remove_contents(50.0)
    assert vial.volume == 50.0
    assert removed_contents["chemicalA"] == 50.0


def test_get_active_vials(session: Session):
    vial1 = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial 1",
        volume=100.0,
        active=True,
    )
    vial2 = Vial(
        position="A2",
        category=0,
        create_new=True,
        name="Test Vial 2",
        volume=100.0,
        active=False,
        session=session,
    )

    active_vials = get_active_vials()
    assert len(active_vials) == 2
    assert active_vials[0].position == "A1"


def test_read_vials(session: Session):
    vial1 = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial 1",
        volume=100.0,
        active=True,
        session=session,
    )

    vial2 = Vial(
        position="A2",
        category=1,
        create_new=True,
        name="Test Vial 2",
        volume=100.0,
        active=True,
        session=session,
    )

    stock_vials, waste_vials = read_vials()
    assert len(stock_vials) == 1
    assert len(waste_vials) == 1
    assert stock_vials[0].position == "A1"
    assert waste_vials[0].position == "A2"


def test_reset_vials(session: Session):
    vial1 = Vial(
        position="A1",
        category=0,
        create_new=True,
        name="Test Vial 1",
        volume=100.0,
        capacity=200.0,
        active=True,
        session=session,
    )

    vial2 = Vial(
        position="A2",
        category=1,
        create_new=True,
        name="Test Vial 2",
        volume=100.0,
        capacity=200.0,
        active=True,
        session=session,
    )

    reset_vials("stock")
    assert vial1.volume == 200.0
    assert vial1.contamination == 0
    assert vial2.volume == 100.0  # Waste vial should not be reset

    reset_vials("waste")
    assert vial2.volume == 200.0
    assert vial2.contamination == 0
