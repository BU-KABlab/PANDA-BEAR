import unittest
from unittest.mock import Mock
import nesp_lib
from pump_control import Pump, MockPump
from mill_control import MockMill
from sartorius_local.mock import Scale as MockScale

class TestPump(unittest.TestCase):
    """Test case for the Pump class."""

    def setUp(self):
        """Set up the test case."""
        self.pump = Pump(mill=MockMill(), scale=MockScale())

    def test_withdraw(self):
        """Test the withdraw method of the Pump class."""
        # Test withdrawing from a vial
        vial = Mock()
        vial.update_volume.return_value = None
        self.pump.run_pump = Mock(return_value=10.0)
        self.pump.update_pipette_volume = Mock()
        self.pump.withdraw(100.0, solution=vial, rate=0.5)
        vial.update_volume.assert_called_once_with(-100.0)
        self.pump.update_pipette_volume.assert_called_once_with(10.0)

        # Test withdrawing without a vial
        self.pump.run_pump = Mock(return_value=10.0)
        self.pump.update_pipette_volume = Mock()
        result = self.pump.withdraw(100.0)
        self.assertIsNone(result)
        self.pump.update_pipette_volume.assert_called_once_with(10.0)

    def test_infuse(self):
        """Test the infuse method of the Pump class."""
        # Test infusing into a vial
        vial = Mock()
        vial.update_volume.return_value = None
        self.pump.run_pump = Mock(return_value=10.0)
        self.pump.update_pipette_volume = Mock()
        self.pump.infuse(100.0, being_infused=vial, infused_into=vial, rate=0.5)
        vial.update_volume.assert_called_once_with(100.0)
        self.pump.update_pipette_volume.assert_called_once_with(10.0)

        # Test infusing without a vial
        self.pump.run_pump = Mock(return_value=10.0)
        self.pump.update_pipette_volume = Mock()
        result = self.pump.infuse(100.0)
        self.assertEqual(result, 0)
        self.pump.update_pipette_volume.assert_called_once_with(10.0)

    def test_purge(self):
        """Test the purge method of the Pump class."""
        purge_vial = Mock()
        solution_being_purged = Mock()
        self.pump.infuse = Mock(return_value=purge_vial)
        result = self.pump.purge(purge_vial, solution_being_purged, purge_volume=20.0, pumping_rate=0.5)
        self.assertEqual(result, purge_vial)
        self.pump.infuse.assert_called_once_with(volume_to_infuse=20.0, rate=0.5, being_infused=solution_being_purged, infused_into=purge_vial)

    def test_run_pump(self):
        """Test the run_pump method of the Pump class."""
        self.pump.pump = Mock()
        self.pump.pump.running = False
        self.pump.pump.volume_infused = 10.0
        self.pump.pump.volume_withdrawn = 5.0
        self.pump.scale = Mock()
        self.pump.scale.read_scale.return_value = 20.0
        result = self.pump.run_pump(nesp_lib.PumpingDirection.INFUSE, 10.0, rate=0.5, density=1.0, blowout_ml=2.0, weigh=True)
        self.assertEqual(result, 10.0)
        self.pump.scale.read_scale.assert_called_once()
        self.assertEqual(self.pump.pump.volume_infused, 0.0)
        self.assertEqual(self.pump.pump.volume_withdrawn, 0.0)

    def test_mix(self):
        """Test the mix method of the Pump class."""
        # Test mixing without mix_location
        self.pump.mill = Mock()
        self.pump.mill.current_coordinates.return_value = (1.0, 2.0, 3.0)
        self.pump.mill.set_feed_rate = Mock()
        self.pump.mill.move_center_to_position = Mock()
        self.pump.withdraw = Mock()
        self.pump.infuse = Mock()
        self.pump.mix()
        self.assertEqual(self.pump.withdraw.call_count, 3)
        self.assertEqual(self.pump.infuse.call_count, 3)
        self.pump.mill.current_coordinates.assert_called_once()
        self.assertEqual(self.pump.mill.set_feed_rate.call_count, 2)
        self.assertEqual(self.pump.mill.move_center_to_position.call_count, 2)

        # Test mixing with mix_location
        self.pump.mill = Mock()
        self.pump.mill.move_pipette_to_position = Mock()
        self.pump.withdraw = Mock()
        self.pump.infuse = Mock()
        mix_location = {"x": 1.0, "y": 2.0, "depth": 3.0}
        self.pump.mix(mix_location=mix_location)
        self.assertEqual(self.pump.withdraw.call_count, 3)
        self.assertEqual(self.pump.infuse.call_count, 3)
        self.pump.mill.move_pipette_to_position.assert_called_once_with(1.0, 2.0, 0)
        self.assertEqual(self.pump.mill.move_pipette_to_position.call_count, 2)

class TestMockPump(unittest.TestCase):
    """
    A test case for the MockPump class.
    """

    def setUp(self):
        """
        Set up the test case by creating an instance of MockPump.
        """
        self.pump = MockPump(MockMill(), MockScale())

    def test_withdraw(self):
        """
        Test the withdraw method of MockPump.
        """
        result = self.pump.withdraw(100.0)
        self.assertIsNone(result)

    def test_infuse(self):
        """
        Test the infuse method of MockPump.
        """
        result = self.pump.infuse(100.0)
        self.assertEqual(result, None)

    def test_purge(self):
        """
        Test the purge method of MockPump.
        """
        purge_vial = Mock()
        solution_being_purged = Mock()
        result = self.pump.purge(purge_vial, solution_being_purged, purge_volume=20.0, pumping_rate=0.5)
        self.assertEqual(result, purge_vial)

    def test_run_pump(self):
        """
        Test the run_pump method of MockPump.
        """
        result = self.pump.run_pump(nesp_lib.PumpingDirection.INFUSE, 10.0, rate=0.5, density=1.0, blowout_ml=2.0, weigh=True)
        self.assertIsInstance(result, float)

    def test_mix(self):
        """
        Test the mix method of MockPump.
        """
        self.pump.mix()

if __name__ == "__main__":
    #unittest.main()

    # Test just the TestMockPump
    suite = unittest.TestSuite()
    suite.addTest(TestMockPump('test_withdraw'))
    suite.addTest(TestMockPump('test_infuse'))
    suite.addTest(TestMockPump('test_purge'))
    suite.addTest(TestMockPump('test_run_pump'))
    suite.addTest(TestMockPump('test_mix'))
    runner = unittest.TextTestRunner()
    runner.run(suite)
    
