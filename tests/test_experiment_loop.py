import pytest

from panda_lib.experiment_loop import (
    _check_stock_vials,
    _establish_system_state,
    read_vials,
)
from panda_lib.labware.vials import StockVial
from panda_lib.labware.wellplates import Well, Wellplate


@pytest.fixture
def src_vessel(temp_test_db):
    vial = StockVial("s2")
    return vial


@pytest.fixture
def dst_vessel(temp_test_db):
    dst_vessel = Well("B5", plate_id=123)
    return dst_vessel


@pytest.mark.usefixtures("temp_test_db")
def test_establish_system_state(temp_test_db):
    stock_vials, waste_vials, wellplate = _establish_system_state()
    assert isinstance(stock_vials, list)
    assert isinstance(waste_vials, list)
    assert isinstance(wellplate, Wellplate)


def test_check_stock_vials(temp_test_db):
    stock_vials, _ = read_vials("stock")
    exp_soln = {"solution1": {"volume": 500, "repeated": 1}}
    sufficient, check_table = _check_stock_vials(exp_soln, stock_vials)
    assert sufficient is True
    assert "sufficient" in check_table


def test_validate_stock_solutions(temp_test_db):
    stock_vials, _ = read_vials("stock")

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


@pytest.mark.usefixtures("temp_test_db")
def test_insufficient_volume_error(temp_test_db):
    stock_vial_list = [
        StockVial(
            name="Vial1",
            position="s1",
            category=0,
            contents={"solution1": 1000},
            volume=1000,
            create_new=True,
        )
    ]
    exp_soln = {"solution1": {"volume": 2000, "repeated": 1}}
    passes, table = _check_stock_vials(exp_soln, stock_vial_list)
    assert passes is False
