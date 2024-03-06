"""_summary_
"""
import unittest
from unittest.mock import Mock

import nesp_lib
from mill_control import MockMill
from pump_control import MockPump, Pipette, Pump
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

    def test_run_pump(self):
        """Test the run_pump method of the Pump class."""
        self.pump.pump = Mock()
        self.pump.pump.running = False
        self.pump.pump.volume_infused = 10.0
        self.pump.pump.volume_withdrawn = 5.0
        self.pump.scale = Mock()
        self.pump.scale.read_scale.return_value = 20.0
        result = self.pump.run_pump(
            nesp_lib.PumpingDirection.INFUSE,
            10.0,
            rate=0.5,
            density=1.0,
            blowout_ml=2.0,
            weigh=True,
        )
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

    def test_run_pump(self):
        """
        Test the run_pump method of MockPump.
        """
        result = self.pump.run_pump(
            nesp_lib.PumpingDirection.INFUSE,
            10.0,
            rate=0.5,
            density=1.0,
            blowout_ml=2.0,
            weigh=True,
        )
        self.assertIsInstance(result, float)

    def test_mix(self):
        """
        Test the mix method of MockPump.
        """
        self.pump.mix()

class TestPipette(unittest.TestCase):
    """Test case for the Pipette class."""

    def setUp(self):
        """Set up the test case."""
        self.pipette = Pipette()

    def test_set_capacity(self):
        """Test the set_capacity method of the Pipette class."""
        self.pipette.set_capacity(1000.0)
        self.assertEqual(self.pipette.capacity_ul, 1000.0)
        self.assertEqual(self.pipette.capacity_ml, 1.0)

    def test_update_contents(self):
        """Test the update_contents method of the Pipette class."""
        self.pipette.update_contents("solution1", 100.0)
        self.assertEqual(self.pipette.contents, {"solution1": 100.0})
        self.assertEqual(self.pipette.volume, 100.0)
        self.assertEqual(self.pipette.volume_ml, 0.1)

    def test_update_volume(self):
        """Test the update_volume method of the Pipette class."""
        self.pipette.volume = 100.0
        self.assertEqual(self.pipette.volume, 100.0)
        self.assertEqual(self.pipette.volume_ml, 0.1)

    def test_update_volume_ml(self):
        """Test the update_volume_ml method of the Pipette class."""
        self.pipette.volume_ml = 0.1
        self.assertEqual(self.pipette.volume, 100.0)
        self.assertEqual(self.pipette.volume_ml, 0.1)

    def test_reset_contents(self):
        """Test the reset_contents method of the Pipette class."""
        self.pipette.update_contents("solution1", 100.0)
        self.pipette.reset_contents()
        self.assertEqual(self.pipette.contents, {})
        self.assertEqual(self.pipette.volume, 0.0)
        self.assertEqual(self.pipette.volume_ml, 0.0)

    def test_update_state_file(self):
        """Test the update_state_file method of the Pipette class."""
        self.pipette.update_state_file()
        self.assertTrue(self.pipette.state_file.exists())

    def test_str(self):
        """Test the __str__ method of the Pipette class."""
        self.pipette.volume = 100.0
        self.assertEqual(str(self.pipette), "Pipette has 100.0 ul of liquid")

def pump_suite():
    # Test just the TestMockPump
    suite = unittest.TestSuite()
    suite.addTest(TestMockPump("test_withdraw"))
    suite.addTest(TestMockPump("test_infuse"))
    suite.addTest(TestMockPump("test_purge"))
    suite.addTest(TestMockPump("test_run_pump"))
    suite.addTest(TestMockPump("test_mix"))
    runner = unittest.TextTestRunner()
    runner.run(suite)

def pipette_suite():
    # Test just the TestPipette
    suite = unittest.TestSuite()
    suite.addTest(TestPipette("test_set_capacity"))
    suite.addTest(TestPipette("test_update_contents"))
    suite.addTest(TestPipette("test_update_volume"))
    suite.addTest(TestPipette("test_update_volume_ml"))
    suite.addTest(TestPipette("test_reset_contents"))
    suite.addTest(TestPipette("test_str"))
    runner = unittest.TextTestRunner()
    runner.run(suite)
if __name__ == "__main__":
    # unittest.main()
    #pump_suite()
    pipette_suite()
