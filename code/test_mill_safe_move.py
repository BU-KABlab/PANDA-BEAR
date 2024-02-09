class MillController:
    def __init__(self, config):
        self.config = {"safe_height_floor": 10}  # Adjust the safe height as needed

    def test_logic(self, current_z, z_coord, fixed_z):
        if current_z != 0 and current_z != z_coord and (not fixed_z or fixed_z):
            # This condition is true if:
            #  - the current Z coordinate is not zero
            #  - it is not equal to the target Z coordinate
            #  - the fixed_z flag is not set (i.e. fixed_z = False) or it is set (i.e. fixed_z = True)
            # Additionally, current_z should be below the safe height.
            if current_z < self.config["safe_height_floor"]:
                print("Testing - Would be moving to Z = 0")
                print(
                    f"Reason:\n\tcurrent_z is below self.config['safe_height_floor'] {current_z < self.config['safe_height_floor']}"
                )
                # self.execute_command("G01 Z0")
                return True
            else:
                print("Testing - Would not be moving to Z = 0")
                print(
                    f"Reason:\n\tcurrent_z is at or above self.config['safe_height_floor'] {current_z >= self.config['safe_height_floor']}"
                )
                return False
        else:
            print("Testing - Would not be moving to Z = 0")
            if current_z == 0:
                print(f"Reason:\n\tcurrent_z is zero")
            elif current_z == z_coord:
                print(f"Reason:\n\tcurrent_z is equal to the target Z coordinate {current_z == z_coord}")
            elif fixed_z:
                print(f"Reason:\n\tfixed_z is set to True")
            else:
                print(f"Reason:\n\tMultiple Conditions not met: current_z = {current_z}, z_coord = {z_coord}, fixed_z = {fixed_z}")
            return False


def test_mill_controller():
    """Test the mill controller logic."""
    config = {"safe_height_floor": 10}  # Adjust the safe height as needed
    mill_controller = MillController(config)

    # Test Scenario 1: Should trigger the command
    current_z = 5
    z_coord = 7
    fixed_z = False

    print("\nTest Scenario 1:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == True

    # Test Scenario 2: Should trigger the command
    current_z = 5
    z_coord = 7
    fixed_z = True

    print("\nTest Scenario 2:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == True

    # Test Scenario 3: Should not trigger the command
    current_z = 7
    z_coord = 7
    fixed_z = False

    print("\nTest Scenario 3:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

    # Test Scenario 4: Should not trigger the command
    current_z = 7
    z_coord = 7
    fixed_z = True

    print("\nTest Scenario 4:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

    # Test Scenario 5: Should not trigger the command
    current_z = 0
    z_coord = 7
    fixed_z = False

    print("\nTest Scenario 5:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

    # Test Scenario 6: Should not trigger the command
    current_z = 0
    z_coord = 7
    fixed_z = True

    print("\nTest Scenario 6:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

    # Test Scenario 7: Should not trigger the command
    current_z = 5
    z_coord = 5
    fixed_z = False

    print("\nTest Scenario 7:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

    # Test Scenario 8: Should not trigger the command
    current_z = 5
    z_coord = 5
    fixed_z = True

    print("\nTest Scenario 8:")
    assert mill_controller.test_logic(current_z, z_coord, fixed_z) == False

if __name__ == "__main__":
    test_mill_controller()
