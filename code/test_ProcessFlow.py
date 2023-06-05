import unittest
import nesp_lib
from unittest.mock import MagicMock
from ProcessFlow import withdraw, infuse

class ProcessFlowTest(unittest.TestCase):
    def setUp(self):
        # Create mock objects for pump and mill
        self.mock_pump = MagicMock()
        self.mock_mill = MagicMock()

    def test_withdraw(self):
        # Set the expected values
        volume = 0.140
        position = {"x": 0, "y": -100, "z": 0}
        depth = -30
        rate = 0.4

        # Call the withdraw function with mock objects
        withdraw(volume, position, depth, rate, self.mock_pump)

        # Assert that the mock pump was called with the expected values
        self.mock_pump.pumping_direction.assert_called_with(nesp_lib.PumpingDirection.WITHDRAW)
        self.mock_pump.pumping_volume.assert_called_with(volume)
        self.mock_pump.pumping_rate.assert_called_with(rate)
        self.mock_pump.run.assert_called()
        self.mock_pump.volume_withdrawn += volume
    
    def test_infuse(self):
            # Set the expected values
            volume = 0.100
            position = {"x": 0, "y": -100, "z": 0}
            depth = -30
            rate = 0.4

            # Call the infuse function with mock objects
            infuse(volume, position, depth, rate, self.mock_pump)

            # Assert that the mock pump was called with the expected values
            self.mock_pump.pumping_direction.assert_called_with(nesp_lib.PumpingDirection.INFUSE)
            self.mock_pump.pumping_volume.assert_called_with(volume)
            self.mock_pump.pumping_rate.assert_called_with(rate)
            self.mock_pump.run.assert_called()
            self.mock_pump.volume_infused += volume

if __name__ == '__main__':
    unittest.main()
