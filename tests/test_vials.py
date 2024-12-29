import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.errors import OverDraftException, OverFillException
from panda_lib.sql_tools.panda_models import Base, Vials
from panda_lib.vials import Vial

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Create the tables in the in-memory database
# Assuming Base.metadata.create_all(engine) is called somewhere in the project setup


@pytest.fixture(scope="function")
def session_maker():
    """Create a new database session for a test."""
    db = SessionLocal
    try:
        yield db
    finally:
        # db.close()
        pass


def test_create_new_vial(session_maker: Session):
    vial = Vial(
        position="A1",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=10000.0,
        capacity=20000.0,
        height=57.0,
        category=1,
    )
    assert vial.vial_data.name == "Test Vial"
    assert vial.vial_data.volume == 10000.0
    assert vial.vial_data.capacity == 20000.0
    assert vial.vial_data.volume_height is not None

    # Verify that the vial in the db matches the vial object
    with session_maker() as session:
        db_vial = session.execute(select(Vials).filter_by(position="A1")).scalar_one()
    assert db_vial.name == "Test Vial"
    assert db_vial.volume == 10000.0
    assert db_vial.capacity == 20000.0
    assert db_vial.volume_height > 0.0


def test_load_existing_vial(session_maker: Session):
    # Create a new vial first
    Vial(
        position="A2",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        category=1,
    )

    # Load the existing vial
    vial = Vial(position="A2", session=session_maker, create_new=False)
    assert vial.vial_data.name == "Test Vial"
    assert vial.vial_data.volume == 100.0


def test_add_contents(session_maker: Session):
    vial = Vial(
        position="A3",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        category=1,
    )

    vial.add_contents({"chemicalA": 50.0}, 50.0)
    assert vial.vial_data.volume == 150.0
    assert vial.vial_data.contents["chemicalA"] == 50.0

    with session_maker() as session:
        db_vial = session.execute(select(Vials).filter_by(position="A3")).scalar_one()
    assert db_vial.volume == 150.0
    assert db_vial.contents["chemicalA"] == 50.0


def test_add_contents_overfill(session_maker: Session):
    vial = Vial(
        position="A4",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=150.0,
        category=1,
    )

    with pytest.raises(OverFillException):
        vial.add_contents({"chemicalA": 100.0}, 100.0)


def test_remove_contents(session_maker: Session):
    vial = Vial(
        position="A5",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        contents={"chemicalA": 100.0},
        category=1,
    )

    removed_contents = vial.remove_contents(50.0)
    assert vial.vial_data.volume == 50.0
    assert removed_contents["chemicalA"] == 50.0

    with session_maker() as session:
        db_vial = session.execute(select(Vials).filter_by(position="A5")).scalar_one()
    assert db_vial.volume == 50.0
    assert db_vial.contents["chemicalA"] == 50.0


def test_remove_contents_overdraft(session_maker: Session):
    vial = Vial(
        position="A66",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=50.0,
        capacity=200.0,
        contents={"chemicalA": 50.0},
        category=1,
    )

    with pytest.raises(OverDraftException):
        vial.remove_contents(100.0)


def test_add_contents_stock_vial(session_maker: Session):
    vial = Vial(
        position="A6",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        category=0,
    )

    with pytest.raises(ValueError):
        vial.add_contents({"chemicalA": 50.0}, 50.0)


def test_reset_vial_stock_vial(session_maker: Session):
    vial = Vial(
        position="A7",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        category=0,
        contents={"chemicalA": 100.0},
    )

    vial.reset_vial()
    assert vial.vial_data.volume == 200.0
    assert vial.vial_data.contents == {"chemicalA": 200.0}


def test_reset_vial_waste(session_maker: Session):
    vial = Vial(
        position="A8",
        session=session_maker,
        create_new=True,
        name="Test Vial",
        volume=100.0,
        capacity=200.0,
        category=1,
    )

    vial.reset_vial()
    assert vial.vial_data.volume == 200.0
    assert vial.vial_data.contamination == 0
    assert vial.vial_data.contents == {}
