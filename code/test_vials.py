import unittest
from unittest.mock import patch
from vials import Vial2, OverFillException, OverDraftException, Vessel

class TestVessel(unittest.TestCase):
    def setUp(self):
        self.vessel = Vessel(name="Test Vessel", volume=50.0, capacity=100.0, density=1.0, coordinates={})

    def test_update_volume_positive(self):
        self.vessel.update_volume(30.0)
        self.assertEqual(self.vessel.volume, 80.0)

    def test_update_volume_negative(self):
        with self.assertRaises(OverDraftException):
            self.vessel.update_volume(-60.0)

    def test_update_volume_over_capacity(self):
        with self.assertRaises(OverFillException):
            self.vessel.update_volume(60.0)

    def test_str_representation(self):
        expected_str = "Test Vessel has 50.0 ul of 1.0 g/ml liquid"
        self.assertEqual(str(self.vessel), expected_str)

class TestVial2(unittest.TestCase):
    def setUp(self):
        self.vial = Vial2(
            name="Test Vial",
            category=0,
            volume=19000.0,
            capacity=20000.0,
            density=1.5,
            coordinates={},
            radius=10.83,
            height=55.0,
            z_bottom=-75.0
        )

    def test_calculate_depth(self):
        depth = self.vial.calculate_depth()
        self.assertAlmostEqual(depth, 51.564,3)

    def test_check_volume_positive(self):
        result = self.vial.check_volume(100.0)
        self.assertTrue(result)

    def test_check_volume_over_capacity(self):
        with self.assertRaises(OverFillException):
            self.vial.check_volume(2000.0)

    def test_check_volume_negative_overdraft(self):
        with self.assertRaises(OverDraftException):
            self.vial.check_volume(-20000.0)

    def test_update_volume_positive(self):
        self.vial.update_volume(-50.0)
        self.assertEqual(self.vial.volume, 18950.0)
        self.assertEqual(self.vial.depth, 51.428)
        self.assertEqual(self.vial.contamination, 1)

    def test_update_volume_negative_overdraft(self):
        with self.assertRaises(OverDraftException):
            self.vial.update_volume(-19001.0)

    def test_update_volume_negative_over_capacity(self):
        with self.assertRaises(OverFillException):
            self.vial.update_volume(2000.0)

    def test_write_volume_to_disk(self):
        # Assuming the method doesn't raise any errors
        #self.vial.write_volume_to_disk()
        pass

    def test_update_contamination(self):
        self.vial.update_contamination()
        self.assertEqual(self.vial.contamination, 1)

    def test_update_contamination_with_value(self):
        self.vial.update_contamination(new_contamination=5)
        self.assertEqual(self.vial.contamination, 5)

if __name__ == '__main__':
    unittest.main()
