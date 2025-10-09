import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.labware.tipracks import Rack
from panda_lib.sql_tools import Base
from panda_lib.sql_tools.models.racks import RackTypes

# In-memory SQLite database
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Seed a simple rack type
with Session(engine) as session:
    session.add(
        RackTypes(
            id=1,
            count=4,
            rows="AB",
            cols=2,
            shape="circular",
            radius_mm=1.0,
            y_spacing=9.0,
            x_spacing=9.0,
            rack_length_mm=10.0,
            rack_width_mm=10.0,
            rack_height_mm=10.0,
            x_offset=0.0,
            y_offset=0.0,
        )
    )
    session.commit()


@pytest.fixture(scope="function")
def session():
    db = SessionLocal
    try:
        yield db
    finally:
        db().close()


def test_rack_creation_and_tip_seeding(session):
    rack = Rack(
        session_maker=session,
        create_new=True,
        type_id=1,
        a1_x=0.0,
        a1_y=0.0,
        orientation=0,
        pickup_height=5.0,
        coordinates={"x": 0.0, "y": 0.0, "z": 5.0},
    )

    assert rack.rack_data.id == 1
    assert len(rack.tips) == 4

    expected = rack.calculate_tip_coordinates("B", 2)
    assert rack.tips["B2"].coordinates == expected
