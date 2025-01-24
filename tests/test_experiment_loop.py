import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.experiment_loop import (
    _check_stock_vials,
    _establish_system_state,
    read_vials,
)
from panda_lib.labware.schemas import VialWriteModel, WellWriteModel
from panda_lib.labware.vials import StockVial
from panda_lib.labware.wellplate import Well, Wellplate
from panda_lib.sql_tools.panda_models import Base, Vials, WellModel

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# populate the database with initial data
with Session(engine) as sesh:
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

    vial2 = VialWriteModel(
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
    )
    sesh.add(Vials(**vial2.model_dump()))

    waste_vial = VialWriteModel(
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


@pytest.fixture
def mock_db_session():
    return SessionLocal


@pytest.fixture
def src_vessel(mock_db_session):
    vial = StockVial("s2", session_maker=mock_db_session)
    return vial


@pytest.fixture
def dst_vessel(mock_db_session):
    dst_vessel = Well("B5", plate_id=123, session_maker=mock_db_session)
    return dst_vessel


def test_establish_system_state(mock_db_session):
    stock_vials, waste_vials, wellplate = _establish_system_state(
        session_maker=mock_db_session
    )
    assert isinstance(stock_vials, list)
    assert isinstance(waste_vials, list)
    assert isinstance(wellplate, Wellplate)


def test_check_stock_vials(mock_db_session):
    stock_vials, _ = read_vials("stock", mock_db_session)
    exp_soln = {"solution1": {"volume": 500, "repeated": 1}}
    sufficient, check_table = _check_stock_vials(exp_soln, stock_vials)
    assert sufficient is True
    assert "sufficient" in check_table


def test_validate_stock_solutions(mock_db_session):
    stock_vials, _ = read_vials("stock", mock_db_session)

    exp_soln_1 = {"solution1": {"volume": 500, "repeated": 1}}
    sufficient_1, check_table_1 = _check_stock_vials(exp_soln_1, stock_vials)
    assert sufficient_1 is True
    assert "sufficient" in check_table_1

    exp_soln_2 = {"edot": {"volume": 10000, "repeated": 1}}
    sufficient_2, check_table_2 = _check_stock_vials(exp_soln_2, stock_vials)
    assert sufficient_2 is True
    assert "sufficient" in check_table_2

    exp_soln_3 = {"rinse": {"volume": 25000, "repeated": 1}}
    sufficient_3, check_table_3 = _check_stock_vials(exp_soln_3, stock_vials)
    assert sufficient_3 is False
    assert "insufficient" in check_table_3

    # Consolidate the check tables
    check_table = {
        **check_table_1,
        **check_table_2,
        **check_table_3,
    }

    sufficient_stock = all([sufficient_1, sufficient_2, sufficient_3])

    assert sufficient_stock is False
    assert "insufficient" in check_table


def test_insufficient_volume_error(mock_db_session):
    stock_vial_list = [
        StockVial(
            name="Vial1",
            position="s1",
            category=0,
            contents={"solution1": 1000},
            volume=1000,
            session_maker=mock_db_session,
            create_new=True,
        )
    ]
    exp_soln = {"solution1": {"volume": 2000, "repeated": 1}}
    passes, table = _check_stock_vials(exp_soln, stock_vial_list)
    assert passes is False
