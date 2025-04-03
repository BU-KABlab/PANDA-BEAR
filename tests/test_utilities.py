from panda_lib.utilities import Coordinates, solve_vials_ilp


def test_solve_vials_ilp():
    # Test case 1
    vial_concentration_map = {"A": 1.0, "B": 2.0, "C": 3.0}
    v_total = 100.0
    c_target = 2.5
    expected_volumes = {"A": 25.0, "B": 0.0, "C": 75.0}
    expected_deviation = 0.0

    volumes, deviation, locations = solve_vials_ilp(
        vial_concentration_map, v_total, c_target
    )

    assert locations == expected_volumes
    assert deviation == expected_deviation

    # Test case 2
    vial_concentration_map = {"A": 0.5, "B": 1.0, "C": 1.5, "D": 2.0}
    v_total = 200.0
    c_target = 1.25
    expected_volumes_a = {"A": 100.0, "B": 0.0, "C": 0.0, "D": 100.0}
    expected_volumes_b = {"A": 0.0, "B": 100.0, "C": 100.0, "D": 0}
    expected_deviation = 0.0

    volumes, deviation, locations = solve_vials_ilp(
        vial_concentration_map, v_total, c_target
    )

    assert locations == expected_volumes_a or locations == expected_volumes_b
    assert deviation == expected_deviation


def test_coordinates():
    # Test case 1
    x = 1.23
    y = 4.56
    z = 7.89
    coordinates = Coordinates(x, y, z)

    assert coordinates.x == x
    assert coordinates.y == y
    assert coordinates.z == z

    # Test case 2
    x = "1.23"
    y = "4.56"
    z = "7.89"
    coordinates = Coordinates(x, y, z)

    assert coordinates.x == 1.23
    assert coordinates.y == 4.56
    assert coordinates.z == 7.89

    # Test case 3
    # Establish a set of coordinates then modify them
    x = 1.23
    y = 4.56
    z = 7.89
    coordinates = Coordinates(x, y, z)

    new_x = 9.87
    new_y = 6.54
    new_z = 3.21
    coordinates.x = new_x
    coordinates.y = new_y
    coordinates.z = new_z

    assert coordinates.x == new_x
    assert coordinates.y == new_y
    assert coordinates.z == new_z
