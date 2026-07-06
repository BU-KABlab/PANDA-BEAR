from unittest.mock import Mock, patch

import pytest

from panda_lib.hardware.grbl_cnc_mill.driver import Mill
from panda_lib.hardware.grbl_cnc_mill.tools import Coordinates, ToolManager

# The mill now runs in the CubOS deck-origin frame: front-left-bottom origin
# (0,0,0), positive max corner (x_max, y_max, z_max). These fixtures and the
# expected G-code below are all expressed in that positive deck frame.


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
        mill.working_volume = Coordinates(x=401.0, y=301.0, z=85.0)
        mill.working_volume_min = Coordinates(x=0.0, y=0.0, z=0.0)
        mill.max_z_height = 85.0
        mill.safe_z_height = 75.0
        # Mock tool manager
        mill.tool_manager = ToolManager()
        return mill


@pytest.fixture
def mock_current_coordinates():
    """Mock the current_coordinates method"""
    return Coordinates(x=100, y=100, z=30), Coordinates(x=100, y=100, z=30)


def test_move_to_positions_single_target(mock_mill):
    """Test moving to a single target position"""
    # Mock current_coordinates to return a known position
    mock_mill.current_coordinates = Mock(return_value=Coordinates(100, 100, 30))

    target = Coordinates(x=200, y=200, z=40)
    mock_mill.move_to_positions([target], tool="center", safe_move_required=True)

    # Verify execute_command was called with the expected commands
    # Lookup the tool offset for the center in the config
    offset = mock_mill.tool_manager.get_offset("center")
    # formulate the expected command based on the offset
    expected_x = offset.x + target.x
    expected_y = offset.y + target.y
    expected_z = offset.z + target.z

    expected_commands = (
        f"G01 Z{mock_mill.max_z_height}\n"
        f"G01 X{expected_x} Y{expected_y}\n"
        f"G01 Z{expected_z}"
    )
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_multiple_targets(mock_mill):
    """Test moving to multiple target positions"""
    mock_mill.current_coordinates = Mock(return_value=(Coordinates(100, 100, 30)))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    targets = [Coordinates(x=200, y=200, z=40), Coordinates(x=300, y=200, z=25)]

    mock_mill.move_to_positions(targets, tool="center", safe_move_required=True)

    # Verify execute_command was called with commands for both movements
    offset = mock_mill.tool_manager.get_offset("center")
    # formulate the expected command based on the offset
    expected_y = offset.y + targets[0].y
    max_z = mock_mill.max_z_height

    expected_commands = (
        f"G01 Z{max_z}\nG01 X200.0 Y{expected_y}\nG01 Z40.0\n"
        f"G01 Z{max_z}\nG01 X300.0 Y{expected_y}\nG01 Z25.0"
    )
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_already_at_target(mock_mill):
    """Test when current position is already at target"""
    current_pos = Coordinates(100, 100, 30)
    mock_mill.current_coordinates = Mock(return_value=current_pos)

    # Try to move to current position
    mock_mill.move_to_positions([current_pos], tool="mill", safe_move_required=True)

    # Verify no movement commands were sent
    mock_mill.ser_mill.write.assert_not_called()


def test_move_to_positions_invalid_coordinates(mock_mill):
    """Test moving to invalid coordinates (negatives are outside the deck frame)"""
    mock_mill.current_coordinates = Mock(
        return_value=(Coordinates(100, 100, 30), Coordinates(100, 100, 30))
    )

    # Negative coordinates are outside the front-left-bottom deck envelope
    invalid_target = Coordinates(x=-100, y=-100, z=-50)  # Invalid coordinates

    with pytest.raises(ValueError, match="coordinate out of range"):
        mock_mill.move_to_positions(
            [invalid_target], tool="center", safe_move_required=True
        )


def test_move_to_positions_above_max_rejected(mock_mill):
    """Coordinates beyond the positive max corner are rejected"""
    mock_mill.current_coordinates = Mock(return_value=Coordinates(100, 100, 30))

    # x beyond x_max (401) is out of range
    invalid_target = Coordinates(x=500, y=100, z=40)

    with pytest.raises(ValueError, match="x coordinate out of range"):
        mock_mill.move_to_positions(
            [invalid_target], tool="center", safe_move_required=True
        )


def test_move_to_positions_without_safe_move(mock_mill):
    """Test moving without safe move requirement"""
    mock_mill.current_coordinates = Mock(return_value=Coordinates(100, 100, 30))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    target = Coordinates(x=200, y=200, z=40)
    mock_mill.move_to_positions([target], tool="mill", safe_move_required=False)

    # Verify direct movement commands were sent
    expected_commands = "G01 X200.0\nG01 Y200.0\nG01 Z40.0"
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )


def test_move_to_positions_with_tool_offset(mock_mill):
    """Test moving with tool offset (offsets are relative vectors, frame-agnostic)"""
    mock_mill.current_coordinates = Mock(return_value=Coordinates(100, 100, 30))
    mock_mill.ser_mill.readline.return_value = b"ok\r\n"
    # Set up a tool with offset
    tool_offset = Coordinates(x=10, y=10, z=10)
    mock_mill.tool_manager.add_tool("test_tool", tool_offset)

    target = Coordinates(x=200, y=200, z=40)
    mock_mill.move_to_positions([target], tool="test_tool", safe_move_required=True)

    # Verify commands include offset adjustments
    expected_commands = (
        f"G01 Z{mock_mill.max_z_height}\n"
        "G01 X210.0 Y210.0\n"
        "G01 Z50.0"  # Adjusted for offset
    )
    mock_mill.ser_mill.write.assert_called_with(
        expected_commands.encode(encoding="ascii") + b"\n"
    )

    mock_mill.tool_manager.delete_tool("test_tool")


# --- Deck-frame-specific coverage -------------------------------------------


def test_working_volume_is_positive_deck_frame():
    """read_working_volume returns the positive max corner from $130/$131/$132"""
    with patch("serial.Serial"):
        mill = Mill()
    assert mill.working_volume.x > 0
    assert mill.working_volume.y > 0
    assert mill.working_volume.z > 0
    assert (
        mill.working_volume_min.x,
        mill.working_volume_min.y,
        mill.working_volume_min.z,
    ) == (0.0, 0.0, 0.0)
    # max_z_height is the top of the envelope; safe height sits just below it
    assert mill.max_z_height == mill.working_volume.z
    assert mill.safe_z_height == mill.max_z_height - 10.0


def test_validate_accepts_deck_frame_edges(mock_mill):
    """Both envelope edges (origin and max corner) are valid"""
    mock_mill._validate_target_coordinates(Coordinates(0.0, 0.0, 0.0))
    mock_mill._validate_target_coordinates(Coordinates(401.0, 301.0, 85.0))


@pytest.mark.parametrize(
    "bad",
    [
        Coordinates(-1.0, 100.0, 40.0),  # x below origin
        Coordinates(100.0, -1.0, 40.0),  # y below origin
        Coordinates(100.0, 100.0, -1.0),  # z below deck bottom
        Coordinates(402.0, 100.0, 40.0),  # x beyond max
        Coordinates(100.0, 302.0, 40.0),  # y beyond max
        Coordinates(100.0, 100.0, 86.0),  # z beyond top
    ],
)
def test_validate_rejects_outside_envelope(mock_mill, bad):
    """Anything outside [min, max] on any axis is rejected"""
    with pytest.raises(ValueError, match="coordinate out of range"):
        mock_mill._validate_target_coordinates(bad)


def test_calculate_target_deck_frame(mock_mill):
    """Target calc adds the (relative) tool offset and clamps Z to the envelope"""
    goto = Coordinates(200.0, 200.0, 40.0)
    current = Coordinates(100.0, 100.0, 30.0)
    offsets = Coordinates(0.0, 0.0, 0.0)
    target = mock_mill._calculate_target_coordinates(goto, current, offsets)
    assert (target.x, target.y, target.z) == (200.0, 200.0, 40.0)

    # Z below the deck floor clamps up to z_min + 3
    low = mock_mill._calculate_target_coordinates(
        Coordinates(200.0, 200.0, -5.0), current, offsets
    )
    assert low.z == mock_mill.working_volume_min.z + 3

    # Z above the ceiling clamps down to max_z_height
    high = mock_mill._calculate_target_coordinates(
        Coordinates(200.0, 200.0, 500.0), current, offsets
    )
    assert high.z == mock_mill.max_z_height


def test_current_coordinates_reads_wpos(mock_mill):
    """With $10=0 the driver parses WPos (no MPos pull-off correction)"""
    mock_mill.config["$10"] = "0"
    mock_mill.read = Mock(
        return_value="<Idle|WPos:100.0,50.0,20.0|Bf:15,127|FS:0,0>"
    )
    coords = mock_mill.current_coordinates()
    assert (coords.x, coords.y, coords.z) == (100.0, 50.0, 20.0)


def test_set_deck_work_offset_pins_home_to_max_corner(mock_mill):
    """homing_sequence's G54 step pins the home corner to (x_max,y_max,z_max)"""
    mock_mill.execute_command = Mock(return_value="ok")
    mock_mill.set_grbl_setting = Mock(return_value="ok")

    mock_mill.set_deck_work_offset()

    # $10 switched to WPos reporting
    mock_mill.set_grbl_setting.assert_any_call("10", "0")
    assert mock_mill.config["$10"] == "0"

    sent = [c.args[0] for c in mock_mill.execute_command.call_args_list]
    assert "G90" in sent
    assert "G54" in sent
    assert "G92.1" in sent
    # The current (home) position is assigned the deck-frame max corner
    assert any(
        s.startswith("G10 L20 P1")
        and "X401.0" in s
        and "Y301.0" in s
        and "Z85.0" in s
        for s in sent
    )
