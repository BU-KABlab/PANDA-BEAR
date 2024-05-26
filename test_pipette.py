import time
import unittest
from decimal import Decimal, getcontext

from epanda_lib.pipette import Pipette

getcontext().prec = 6

class TestPipette(unittest.TestCase):
    """
    Test the Pipette class.
    """

    def setUp(self):
        """
        Set up the test by creating a pipette with capacity of 1000 ul.
        """
        self.pipette = Pipette(Decimal(200))
        self.assertEqual(self.pipette.capacity_ul, Decimal(200))
        self.assertEqual(self.pipette.capacity_ml, Decimal('0.2'))
        time.sleep(1)

    def test_set_capacity(self):
        """
        Test setting the capacity of the pipette.
        """
        time.sleep(1)
        self.pipette.set_capacity(Decimal(500))
        self.assertEqual(self.pipette.capacity_ul, Decimal(500))
        self.assertEqual(self.pipette.capacity_ml, Decimal('0.5'))

        # Reset the capacity
        self.pipette.set_capacity(Decimal(200))

        # Test setting negative capacity
        with self.assertRaises(ValueError):
            self.pipette.set_capacity(Decimal(-100))

    def test_update_contents(self):
        """
        Test updating the contents of the pipette.
        """
        time.sleep(1)
        self.pipette.update_contents("Solution A", Decimal(200))
        self.assertEqual(self.pipette.contents["Solution A"], Decimal(200))

        # Test negative content change
        self.pipette.update_contents("Solution A", Decimal(-50))
        self.assertEqual(self.pipette.contents["Solution A"], Decimal(150))

    def test_volume(self):
        """
        Test setting and getting the volume of the pipette.
        """
        time.sleep(1)
        self.pipette.volume = Decimal(300)
        self.assertEqual(self.pipette.volume, Decimal(300))

        # Test setting negative volume
        with self.assertRaises(ValueError):
            self.pipette.volume = Decimal(-100)

    def test_volume_ml(self):
        """
        Test setting and getting the volume of the pipette in ml.
        """
        time.sleep(1)
        self.pipette.volume_ml = Decimal('0.5')
        self.assertEqual(self.pipette.volume_ml, Decimal('0.5'))

        # Test setting negative volume in ml
        with self.assertRaises(ValueError):
            self.pipette.volume_ml = Decimal(-0.2)

    def test_liquid_volume(self):
        """
        Test getting the volume of liquid in the pipette.
        """
        time.sleep(1)
        self.pipette.update_contents("Solution A", Decimal(200))
        self.pipette.update_contents("Solution B", Decimal(150))
        self.assertEqual(self.pipette.liquid_volume(), Decimal(350))

    def test_reset_contents(self):
        """
        Test resetting the contents of the pipette.
        """
        time.sleep(1)
        self.pipette.update_contents("Solution A", Decimal(200))
        self.pipette.reset_contents()
        self.assertEqual(self.pipette.contents, {})
        self.assertEqual(self.pipette.volume, Decimal(0))
        self.assertEqual(self.pipette.volume_ml, Decimal(0))


if __name__ == "__main__":
    unittest.main()
