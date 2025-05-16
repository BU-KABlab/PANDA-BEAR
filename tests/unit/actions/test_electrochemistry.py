import logging
from unittest.mock import patch

import pytest

from panda_lib.errors import CAFailure, CVFailure, OCPError, OCPFailure
from panda_lib.experiments.experiment_types import ExperimentStatus


# Set up pytest
@pytest.fixture(autouse=True)
def setup_testing():
    """Setup test environment with mocks."""
    with (
        patch("panda_lib.actions.electrochemistry.TESTING", True),
        patch(
            "panda_lib.actions.electrochemistry.read_testing_config", return_value=True
        ),
        patch("panda_lib.actions.electrochemistry.read_config"),
        patch("panda_lib.actions.electrochemistry.config"),
        patch("panda_lib.actions.electrochemistry.echem"),
        patch("panda_lib.actions.electrochemistry.chrono_parameters"),
        patch("panda_lib.actions.electrochemistry.cv_parameters"),
        patch("panda_lib.actions.electrochemistry.potentiostat_ocp_parameters"),
    ):
        yield


# Test open_circuit_potential (ocp)
@pytest.mark.parametrize(
    "testing,file_tag",
    [
        (True, "test_tag"),
        (True, None),
        (False, "test_tag"),
    ],
)
def test_open_circuit_potential(
    mock_gamry_potentiostat, mock_experiment, mock_ocp_parameters, testing, file_tag
):
    """Test open circuit potential measurement."""
    with (
        patch(
            "panda_lib.actions.electrochemistry.echem",
            return_value=mock_gamry_potentiostat,
        ) as _,
        patch(
            "panda_lib.actions.electrochemistry.potentiostat_ocp_parameters",
            mock_ocp_parameters,
        ),
    ):
        from panda_lib.actions.electrochemistry import open_circuit_potential

        # Test successful OCP
        result = open_circuit_potential(
            file_tag=file_tag, exp=mock_experiment, testing=testing
        )

        # Verify function behavior
        assert result == (True, -0.5)
        mock_gamry_potentiostat.pstatconnect.assert_called_once()
        mock_gamry_potentiostat.pstatdisconnect.assert_called_once()
        mock_gamry_potentiostat.OCP.assert_called_once()
        mock_gamry_potentiostat.setfilename.assert_called_once()
        mock_experiment.results.set_ocp_file.assert_called_once()

        # Test with OCP failure
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_gamry_potentiostat.check_vf_range.return_value = (False, -0.5)

        with pytest.raises(OCPError):
            open_circuit_potential(
                file_tag=file_tag, exp=mock_experiment, testing=testing
            )

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)


# Test ocp_check function
def test_ocp_check(mock_experiment, mock_toolkit, mock_well):
    """Test OCP check function."""
    with patch(
        "panda_lib.actions.electrochemistry.ocp",
        side_effect=[
            (True, -0.5),
            (False, 0.0),
            (True, -0.5),
            (False, 1.5),
            (False, 0.5),
        ],
    ) as mock_ocp:
        from panda_lib.actions.electrochemistry import ocp_check

        logger = logging.getLogger("test")

        # Test successful OCP
        ocp_check(mock_experiment, mock_well, "test_tag", mock_toolkit, logger)
        mock_toolkit.mill.safe_move.assert_called_once()
        mock_ocp.assert_called_with(file_tag="test_tag", exp=mock_experiment)

        # Test OCP fails with near-zero potential (retry)
        mock_toolkit.reset_mock()
        mock_ocp.reset_mock()

        ocp_check(mock_experiment, mock_well, "test_tag", mock_toolkit, logger)
        assert mock_toolkit.mill.safe_move.call_count == 2
        assert mock_ocp.call_count == 2

        # Test OCP fails with high potential (> 1V)
        mock_toolkit.reset_mock()
        mock_experiment.reset_mock()

        with pytest.raises(OCPError):
            ocp_check(mock_experiment, mock_well, "test_tag", mock_toolkit, logger)

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)

        # Test OCP fails with other potential value
        mock_toolkit.reset_mock()
        mock_experiment.reset_mock()

        with pytest.raises(OCPError):
            ocp_check(mock_experiment, mock_well, "test_tag", mock_toolkit, logger)

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)


# Test perform_chronoamperometry (ca)
def test_perform_chronoamperometry(
    mock_gamry_potentiostat, mock_experiment, mock_chrono_parameters
):
    """Test chronoamperometry function."""
    with (
        patch(
            "panda_lib.actions.electrochemistry.echem",
            return_value=mock_gamry_potentiostat,
        ) as _,
        patch(
            "panda_lib.actions.electrochemistry.chrono_parameters",
            return_value=mock_chrono_parameters,
        ),
    ):
        from panda_lib.actions.electrochemistry import perform_chronoamperometry

        # Test successful CA
        _ = perform_chronoamperometry(mock_experiment, "test_tag")

        # Verify function behavior
        mock_gamry_potentiostat.pstatconnect.assert_called_once()
        mock_gamry_potentiostat.pstatdisconnect.assert_called_once()
        mock_gamry_potentiostat.OCP.assert_called_once()
        mock_gamry_potentiostat.chrono.assert_called_once()

        # Assertions for OCP failure
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_gamry_potentiostat.check_vf_range.return_value = (False, -0.5)

        with pytest.raises(OCPError):
            perform_chronoamperometry(mock_experiment, "test_tag")

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)

        # Assertions for CA failure
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_gamry_potentiostat.check_vf_range.return_value = (True, -0.5)
        mock_gamry_potentiostat.chrono.side_effect = Exception("CA failure")

        with pytest.raises(CAFailure):
            perform_chronoamperometry(mock_experiment, "test_tag")

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)


# Test perform_cyclic_voltammetry (cv)
def test_perform_cyclic_voltammetry(
    mock_gamry_potentiostat, mock_experiment, mock_cv_parameters
):
    """Test cyclic voltammetry function."""
    with (
        patch(
            "panda_lib.actions.electrochemistry.echem",
            return_value=mock_gamry_potentiostat,
        ) as _,
        patch(
            "panda_lib.actions.electrochemistry.cv_parameters",
            return_value=mock_cv_parameters,
        ),
        patch("panda_lib.actions.electrochemistry.potentiostat_ocp_parameters"),
    ):
        from panda_lib.actions.electrochemistry import perform_cyclic_voltammetry

        # Test successful CV
        _ = perform_cyclic_voltammetry(mock_experiment, "test_tag")

        # Verify function behavior
        mock_gamry_potentiostat.pstatconnect.assert_called_once()
        mock_gamry_potentiostat.pstatdisconnect.assert_called_once()
        mock_gamry_potentiostat.OCP.assert_called_once()
        mock_gamry_potentiostat.cyclic.assert_called_once()

        # Test with baseline flag set
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_experiment.baseline = 1

        _ = perform_cyclic_voltammetry(mock_experiment, "test_tag")
        mock_experiment.set_status_and_save.assert_any_call(ExperimentStatus.BASELINE)

        # Test OCP failure
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_gamry_potentiostat.check_vf_range.return_value = (False, -0.5)

        with pytest.raises(OCPFailure):
            perform_cyclic_voltammetry(mock_experiment, "test_tag")

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)

        # Test CV failure
        mock_gamry_potentiostat.reset_mock()
        mock_experiment.reset_mock()
        mock_gamry_potentiostat.check_vf_range.return_value = (True, -0.5)
        mock_gamry_potentiostat.cyclic.side_effect = CVFailure("cv_test", "well_test")

        with pytest.raises(CVFailure):
            perform_cyclic_voltammetry(mock_experiment, "test_tag")

        mock_experiment.set_status_and_save.assert_called_with(ExperimentStatus.ERROR)


# Test move_to_and_perform_cv
def test_move_to_and_perform_cv(mock_experiment, mock_toolkit, mock_well):
    """Test move_to_and_perform_cv function."""
    with (
        patch("panda_lib.actions.electrochemistry.ocp_check") as mock_ocp_check,
        patch(
            "panda_lib.actions.electrochemistry.perform_cyclic_voltammetry"
        ) as mock_cv,
    ):
        from panda_lib.actions.electrochemistry import move_to_and_perform_cv

        logger = logging.getLogger("test")

        # Test successful execution
        move_to_and_perform_cv(
            mock_experiment, mock_toolkit, "test_tag", mock_well, logger
        )

        mock_ocp_check.assert_called_once()
        mock_cv.assert_called_once()

        # Test OCP failure
        mock_ocp_check.reset_mock()
        mock_cv.reset_mock()
        mock_ocp_check.side_effect = OCPFailure(
            mock_experiment.experiment_id, mock_experiment.well_id
        )

        with pytest.raises(OCPFailure):
            move_to_and_perform_cv(
                mock_experiment, mock_toolkit, "test_tag", mock_well, logger
            )
        mock_ocp_check.assert_called_once()
        mock_cv.assert_not_called()

        # Test CV failure
        mock_ocp_check.reset_mock()
        mock_cv.reset_mock()
        mock_ocp_check.side_effect = None
        mock_cv.side_effect = CVFailure("cv_test", "well_test")

        with pytest.raises(CVFailure):
            move_to_and_perform_cv(
                mock_experiment, mock_toolkit, "test_tag", mock_well, logger
            )
        mock_ocp_check.assert_called_once()
        mock_cv.assert_called_once()
