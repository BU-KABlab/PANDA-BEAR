import pytest


def should_move_to_zero_first(
    current_x,
    current_y,
    current_z,
    offset_x_coord,
    offset_y_coord,
    offset_z_coord,
    safe_floor_height,
):
    if offset_z_coord not in (0, current_z):
        if current_z == 0:
            return False
        elif current_x != offset_x_coord and current_y != offset_y_coord:
            return current_z < safe_floor_height
        elif current_x == offset_x_coord and current_y == offset_y_coord:
            return False
    else:
        if current_z == 0:
            return False
        elif current_z >= safe_floor_height:
            return False
        elif current_z < safe_floor_height:
            return current_x != offset_x_coord and current_y != offset_y_coord


@pytest.mark.parametrize(
    "current_x, current_y, current_z, offset_x_coord, offset_y_coord, offset_z_coord, safe_floor_height, expected",
    [
        (1, 2, 4, 3, 4, 6, 10, True),  # Test case 1
        (1, 2, 5, 1, 2, 6, 10, False),  # Test case 2
        (1, 2, 0, 3, 4, 0, 10, False),  # Test case 3
        (1, 2, 5, 3, 4, 6, 5, False),  # Test case 4
        (1, 2, 4, 1, 2, 6, 5, False),  # Test case 5
        (1, 2, 0, 3, 4, 6, 5, False),  # Test case 6
        (1, 2, 5, 3, 4, 0, 10, True),  # Test case 7
        (1, 2, 0, 3, 4, 0, 10, False),  # Test case 8
    ],
)
def test_should_move_to_zero_first(
    current_x,
    current_y,
    current_z,
    offset_x_coord,
    offset_y_coord,
    offset_z_coord,
    safe_floor_height,
    expected,
):
    assert (
        should_move_to_zero_first(
            current_x,
            current_y,
            current_z,
            offset_x_coord,
            offset_y_coord,
            offset_z_coord,
            safe_floor_height,
        )
        == expected
    )


if __name__ == "__main__":
    pytest.main()
