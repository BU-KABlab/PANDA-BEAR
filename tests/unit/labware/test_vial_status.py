import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from panda_lib.sql_tools import Base, Vials, VialStatus


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_vial_status_generation(db_session):
    """
    Insert two vials with the same position but different timestamps,
    and verify that the VialStatus view model only returns the most recent one
    even though both are active.
    """
    vial1 = Vials(
        position="A1",
        category=1,
        name="VialOne",
        viscosity_cp=1.0,
        concentration=1.0,
        density=1.0,
        height=1.0,
        radius=1.0,
        volume=1.0,
        capacity=1.0,
        contamination=0,
        coordinates={"x": 0, "y": 0, "z": 0},
        base_thickness=1.0,
        dead_volume=1.0,
        active=1,
        updated="2023-10-01T10:00:00Z",
        panda_unit_id=99,
    )
    vial2 = Vials(
        position="A1",
        category=1,
        name="VialTwo",
        viscosity_cp=1.0,
        concentration=1.0,
        density=1.0,
        height=1.0,
        radius=1.0,
        volume=1.0,
        capacity=1.0,
        contamination=0,
        coordinates={"x": 2, "y": 0, "z": 0},
        base_thickness=1.0,
        dead_volume=1.0,
        active=1,
        updated="2023-10-02T10:00:00Z",
        panda_unit_id=99,
    )
    db_session.add(vial1)
    db_session.add(vial2)
    db_session.commit()

    # Query the VialStatus view model
    result = db_session.query(VialStatus).all()

    # We expect only the most recent record for position A1
    assert len(result) == 1
    assert result[0].name == "VialTwo"
    assert result[0].position == "A1"
    assert result[0].coordinates == {"x": 2, "y": 0, "z": 0}

    # Check that the properties of the VialStatus view model are correct
    assert result[0].x == 2
