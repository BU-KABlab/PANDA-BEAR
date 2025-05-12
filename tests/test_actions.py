import logging

# from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from panda_lib.actions.pipetting import (
    _pipette_action,
    volume_correction,
)
from panda_lib.actions.vessel_handling import (
    _handle_source_vessels,
    solution_selector,
    waste_selector,
)

# from sqlalchemy import create_engine
# from sqlalchemy.orm import Session, sessionmaker
from panda_lib.hardware.panda_pipettes import (
    PipetteDBHandler,
    # PipetteModel,
)
from panda_lib.labware import StockVial, Well

# from panda_lib.labware.schemas import VialWriteModel, WellWriteModel
# from panda_lib.sql_tools.panda_models import Base, Vials, WellModel
from panda_lib.toolkit import (
    Toolkit,
)

logger = MagicMock(
    spec=logging.Logger, info=MagicMock(), debug=MagicMock(), error=MagicMock()
)


@pytest.fixture()
def toolkit():
    from panda_lib.hardware.arduino_interface import MockArduinoLink as ArduinoLink
    from panda_lib.toolkit import (
        MockMill as Mill,
    )
    from panda_lib.toolkit import Pipette

    toolkit = Toolkit(
        pump=Pipette(), mill=Mill(), arduino=ArduinoLink(), scale=MagicMock()
    )
    toolkit.pipette.pipette_tracker = PipetteDBHandler()
    return toolkit


@pytest.fixture
def src_vessel():
    vial = StockVial("s2")
    return vial


@pytest.fixture
def dst_vessel():
    dst_vessel = Well("B5", plate_id=123)
    return dst_vessel


@pytest.mark.usefixtures("temp_test_db")
def test_handle_source_vessels(temp_test_db, src_vessel):
    volume = 100.0
    source_concentration = 1.0

    with (
        patch("panda_lib.actions.vessel_handling.read_vials") as mock_read_vials,
        patch(
            "panda_lib.actions.vessel_handling.solve_vials_ilp"
        ) as mock_solve_vials_ilp,
    ):
        mock_read_vials.return_value = (
            [src_vessel],  # stock vials
            [],  # waste vials
        )
        mock_solve_vials_ilp.return_value = (
            {1.0, 100.0},
            0.0,
            {"s2": 100.0},
        )

        selected_source_vessels, source_vessel_volumes = _handle_source_vessels(
            volume,
            src_vessel,
            logger,
            source_concentration,
        )

        assert len(selected_source_vessels) == 1
        assert len(source_vessel_volumes) == 1


@pytest.mark.usefixtures("temp_test_db")
def test_pipette_action(toolkit: Toolkit, src_vessel: StockVial, dst_vessel: Well):
    desired_volume = 100.0

    # Directly patch the instance method on toolkit.arduino
    with patch.object(
        toolkit.arduino, "async_line_break", new_callable=AsyncMock
    ) as mock_line_break:
        # Configure mock to return True first, then False
        mock_line_break.side_effect = [True, False]

        _pipette_action(toolkit, src_vessel, dst_vessel, desired_volume)
        assert toolkit.pipette.pipette_tracker.volume == 0.0
        assert toolkit.pipette.pipette_tracker.volume_ml == 0.0
        assert src_vessel.volume == 19900.0
        assert dst_vessel.well_data.volume == 100.0

        # Verify async_line_break was called
        assert mock_line_break.call_count > 0

        # If you also need to verify async_send was called, you would need to mock that too
        # with a separate patch.object call


def test_volume_correction():
    volume = 100.0
    density = 1.0
    viscosity = 1.0
    corrected_volume = volume_correction(volume, density, viscosity)
    assert corrected_volume == 100.0


def test_solution_selector(temp_test_db):
    solution_name = "test_solution"
    volume = 100.0

    solution = solution_selector(solution_name, volume)
    assert solution.name == "test_solution"


def test_waste_selector(temp_test_db):
    solution_name = "waste"
    volume = 100.0

    waste_vial = waste_selector(solution_name, volume)
    assert waste_vial.name == "waste"


if __name__ == "__main__":
    pytest.main()
