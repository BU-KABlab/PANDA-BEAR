from unittest.mock import Mock, patch

import pytest

from hardware.grbl_cnc_mill.driver import Mill
from hardware.grbl_cnc_mill.tools import Coordinates, ToolManager


@pytest.fixture
def mock_mill():
    """Create a mock mill instance with mocked serial connection"""
    with patch("serial.Serial") as mock_serial_class:
        mock_serial_instance = mock_serial_class.return_value
        mock_serial_instance.read.return_value = b"ok\r\n"
        mock_serial_instance.readline.return_value = b"ok\r\n"
        mock_serial_instance.read_all.return_value = b"ok\r\n"
        mill = Mill()
        mill.ser_mill = mock_serial_instance
        mill.homed = True
        mill.active_connection = True
        mill.max_z_height = 0
        mill.safe_z_height = -10
        mill.working_volume = Coordinates(x=-415.0, y=-300.0, z=-200.0)
        # Mock tool manager
        mill.tool_manager = ToolManager()
        return mill


@pytest.fixture
def mock_current_coordinates():
    """Mock the current_coordinates method"""
    return Coordinates(x=-100, y=-100, z=-50), Coordinates(x=-100, y=-100, z=-50)


def test_move_to_positions_single_target(mock_mill):
    """Test moving to a single target position"""
    # Mock current_coordinates to return a known position
    mock_mill.current_coordinates = Mock(return_value=Coordinates(-100, -100, -50))

    target = Coordinates(x=-200, y=-200, z=-75)
    mock_mill.move_to_positions([target], tool="center", safe_move_required=True)

    # Verify execute_command was called with the expected commands
    expected_commands = "G01 Z0\nG01 X-200.0 Y-200.0\nG01 Z-75.0"
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_multiple_targets(mock_mill):
    """Test moving to multiple target positions"""
    mock_mill.current_coordinates = Mock(return_value=(Coordinates(-100, -100, -50)))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    targets = [Coordinates(x=-200, y=-200, z=-75), Coordinates(x=-300, y=-200, z=-100)]

    mock_mill.move_to_positions(targets, tool="center", safe_move_required=True)

    # Verify execute_command was called with commands for both movements
    expected_commands = "G01 Z0\nG01 X-200.0 Y-200.0\nG01 Z-75.0\nG01 Z0\nG01 X-300.0 Y-200.0\nG01 Z-100.0"
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_already_at_target(mock_mill):
    """Test when current position is already at target"""
    current_pos = Coordinates(-100, -100, -50)
    mock_mill.current_coordinates = Mock(return_value=current_pos)

    # Try to move to current position
    mock_mill.move_to_positions([current_pos], tool="center", safe_move_required=True)

    # Verify no movement commands were sent
    mock_mill.ser_mill.write.assert_not_called()


def test_move_to_positions_invalid_coordinates(mock_mill):
    """Test moving to invalid coordinates"""
    mock_mill.current_coordinates = Mock(
        return_value=(Coordinates(-100, -100, -50), Coordinates(-100, -100, -50))
    )

    # Try to move outside working volume
    invalid_target = Coordinates(x=100, y=100, z=100)  # Invalid coordinates

    with pytest.raises(ValueError, match="coordinate out of range"):
        mock_mill.move_to_positions(
            [invalid_target], tool="center", safe_move_required=True
        )


def test_move_to_positions_without_safe_move(mock_mill):
    """Test moving without safe move requirement"""
    mock_mill.current_coordinates = Mock(return_value=Coordinates(-100, -100, -50))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    target = Coordinates(x=-200, y=-200, z=-75)
    mock_mill.move_to_positions([target], tool="center", safe_move_required=False)

    # Verify direct movement commands were sent
    expected_commands = "G01 X-200.0\nG01 Y-200.0\nG01 Z-75.0"
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_with_tool_offset(mock_mill):
    """Test moving with tool offset"""
    mock_mill.current_coordinates = Mock(return_value=Coordinates(-100, -100, -50))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    # Set up a tool with offset
    tool_offset = Coordinates(x=10, y=10, z=10)
    mock_mill.tool_manager.add_tool("test_tool", tool_offset)

    target = Coordinates(x=-200, y=-200, z=-75)
    mock_mill.move_to_positions([target], tool="test_tool", safe_move_required=True)

    # Verify commands include offset adjustments
    expected_commands = "G01 Z0\nG01 X-190.0 Y-190.0\nG01 Z-65.0"  # Adjusted for offset
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )

    mock_mill.tool_manager.delete_tool("test_tool")
