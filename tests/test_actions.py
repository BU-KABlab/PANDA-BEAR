import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hardware.pipette import (
    Pipette,
    PipetteModel,
)
from panda_lib.actions import (
    _handle_source_vessels,
    _pipette_action,
    solution_selector,
    volume_correction,
    waste_selector,
)
from panda_lib.instrument_toolkit import (
    MockMill as Mill,
)
from panda_lib.instrument_toolkit import (
    MockPump as SyringePump,
)
from panda_lib.instrument_toolkit import (
    Toolkit,
)
from panda_lib.labware.schemas import VialWriteModel, WellWriteModel
from panda_lib.labware.vials import StockVial
from panda_lib.labware.wellplate import Well
from panda_lib.sql_tools.panda_models import Base, Vials, WellModel
from panda_lib.tools.pawduino import MockArduinoLink as ArduinoLink

test_logger = MagicMock(
    spec=logging.Logger, info=MagicMock(), debug=MagicMock(), error=MagicMock()
)

# Test SQLlite DB session_maker
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
    ),
    (2, 200, 0.2, 0, 0, {}, datetime(2024, 12, 27, 1, 52, 35, 724000), 1, 0),
]


with Session(engine) as sesh:
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

    vial = VialWriteModel(
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
    )

    sesh.add(Vials(**vial.model_dump()))

    vial = VialWriteModel(
        position="w1",
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
        coordinates={"x": -4, "y": -106, "z": -83},
        base_thickness=1,
        dead_volume=1000,
    )

    sesh.add(Vials(**vial.model_dump()))

    waste_vial = VialWriteModel(
        position="waste",
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
    )

    sesh.add(Vials(**waste_vial.model_dump()))

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


@pytest.fixture()
def toolkit():
    toolkit = Toolkit(
        pump=SyringePump(), mill=Mill(), arduino=ArduinoLink(), scale=MagicMock()
    )
    toolkit.pump.pipette = Pipette(db_session_maker=SessionLocal)
    return toolkit


@pytest.fixture
def mock_db_session():
    return SessionLocal


@pytest.fixture
def src_vessel():
    vial = StockVial("s2", session_maker=SessionLocal)
    return vial


@pytest.fixture
def dst_vessel():
    dst_vessel = Well("B5", plate_id=123, session_maker=SessionLocal)
    return dst_vessel


def test_handle_source_vessels(mock_db_session, src_vessel):
    volume = 100.0
    source_concentration = 1.0

    with (
        patch("panda_lib.actions.read_vials") as mock_read_vials,
        patch("panda_lib.actions.solve_vials_ilp") as mock_solve_vials_ilp,
    ):
        mock_read_vials.return_value = (
            [
                src_vessel,
            ],
            [],
        )
        mock_solve_vials_ilp.return_value = (
            {1.0, 100.0},
            0.0,
            {"s2": 100.0},
        )

        selected_source_vessels, source_vessel_volumes = _handle_source_vessels(
            volume,
            src_vessel,
            test_logger,
            source_concentration,
            mock_db_session,
        )

        assert len(selected_source_vessels) == 1
        assert len(source_vessel_volumes) == 1


def test_pipette_action(toolkit: Toolkit, src_vessel: StockVial, dst_vessel: Well):
    desired_volume = 100.0

    _pipette_action(toolkit, src_vessel, dst_vessel, desired_volume)
    assert toolkit.pump.pipette.volume == 0.0
    assert toolkit.pump.pipette.volume_ml == 0.0
    assert src_vessel.volume == 19900.0
    assert dst_vessel.well_data.volume == 100.0


def test_volume_correction():
    volume = 100.0
    density = 1.0
    viscosity = 1.0
    corrected_volume = volume_correction(volume, density, viscosity)
    assert corrected_volume == 100.0


def test_solution_selector(mock_db_session):
    solution_name = "test_solution"
    volume = 100.0

    solution = solution_selector(solution_name, volume, mock_db_session)
    assert solution.name == "test_solution"


def test_waste_selector(mock_db_session):
    solution_name = "waste"
    volume = 100.0

    waste_vial = waste_selector(solution_name, volume, mock_db_session)
    assert waste_vial.name == "waste"


if __name__ == "__main__":
    pytest.main()
