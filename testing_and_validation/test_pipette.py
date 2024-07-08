import time
import unittest
from panda_lib.pipette import Pipette
from panda_lib.pipette.sql_pipette import insert_new_pipette

# class TestPipette(unittest.TestCase):
#     """
#     Test the Pipette class.
#     """

#     def setUp(self):
#         """
#         Set up the test by creating a pipette with capacity of 200 ul.
#         """
#         testing_id = insert_new_pipette(999)
#         self.pipette = Pipette(testing_id)
#         self.assertEqual(self.pipette.capacity_ul, 200)
#         self.assertEqual(self.pipette.capacity_ml, 0.2)
#         time.sleep(1)

#     def test_set_capacity(self):
#         """
#         Test setting the capacity of the pipette.
#         """
#         time.sleep(1)
#         self.pipette.set_capacity(500)
#         self.assertEqual(self.pipette.capacity_ul, 500)
#         self.assertEqual(self.pipette.capacity_ml, 0.5)

#         # Reset the capacity
#         self.pipette.set_capacity(200)

#         # Test setting negative capacity
#         with self.assertRaises(ValueError):
#             self.pipette.set_capacity(-100)

#         self.pipette.set_capacity(200)

#     def test_update_contents(self):
#         """
#         Test updating the contents of the pipette.
#         """
#         time.sleep(1)
#         self.pipette.update_contents("Solution A", 200)
#         self.assertEqual(self.pipette.contents["Solution A"], 200)

#         # Test negative content change
#         self.pipette.update_contents("Solution A", -50)
#         self.assertEqual(self.pipette.contents["Solution A"], 150)

#     def test_volume(self):
#         """
#         Test setting and getting the volume of the pipette.
#         """
#         time.sleep(1)
#         self.pipette.volume = 300
#         self.assertEqual(self.pipette.volume, 300)

#         # Test setting negative volume
#         with self.assertRaises(ValueError):
#             self.pipette.volume = -100

#     def test_volume_ml(self):
#         """
#         Test setting and getting the volume of the pipette in ml.
#         """
#         time.sleep(1)
#         self.pipette.volume_ml = 0.5
#         self.assertEqual(self.pipette.volume_ml, 0.5)

#         # Test setting negative volume in ml
#         with self.assertRaises(ValueError):
#             self.pipette.volume_ml = -0.2

#     def test_liquid_volume(self):
#         """
#         Test getting the volume of liquid in the pipette.
#         """
#         time.sleep(1)
#         self.pipette.update_contents("Solution A", 200)
#         self.pipette.update_contents("Solution B", 150)
#         self.assertEqual(self.pipette.liquid_volume(), 350)

#     def test_reset_contents(self):
#         """
#         Test resetting the contents of the pipette.
#         """
#         time.sleep(1)
#         self.pipette.update_contents("Solution A", 200)
#         self.pipette.reset_contents()
#         self.pipette.record_pipette_state()
#         self.assertEqual(self.pipette.contents, {})
#         self.assertEqual(self.pipette.volume, 0)
#         self.assertEqual(self.pipette.volume_ml, 0)

#     def tearDown(self):
#         """
#         Clean up the test by resetting the pipette capacity.
#         """
#         self.pipette.set_capacity(200)


class TestPipette2(unittest.TestCase):
    def setUp(self):
        test_pipette_id = insert_new_pipette(999)
        self.pipette = Pipette(test_pipette_id)
        self.pipette.activate_pipette()

        self.pipette.reset_contents()
        self.assertEqual(self.pipette.capacity_ul, 200)
        self.assertEqual(self.pipette.capacity_ml, 0.2)
        

    def test_set_capacity(self):
        self.pipette.set_capacity(500)
        self.assertEqual(self.pipette.capacity_ul, 500)
        self.assertEqual(self.pipette.capacity_ml, 0.5)

    def test_update_contents(self):
        self.pipette.update_contents("Solution A", 200)
        self.assertEqual(self.pipette.contents["Solution A"], 200)

    def test_volume(self):
        self.pipette.volume = 300
        self.assertEqual(self.pipette.volume, 300)

    def test_volume_ml(self):
        self.pipette.volume_ml = 0.5
        self.assertEqual(self.pipette.volume_ml, 0.5)

    def test_liquid_volume(self):
        self.pipette.update_contents("Solution A", 200)
        self.pipette.update_contents("Solution B", 150)
        self.assertEqual(self.pipette.liquid_volume(), 350)
        self.assertEqual(self.pipette._volume_ul, 350)

    def test_reset_contents(self):
        self.pipette.update_contents("Solution A", 200)
        self.pipette.reset_contents()
        self.assertEqual(self.pipette.contents, {})
        self.assertEqual(self.pipette.volume, 0)
        self.assertEqual(self.pipette.volume_ml, 0)

    def tearDown(self) -> None:
        self.pipette.set_capacity(200)
        self.pipette.reset_contents()


def main():
    unittest.main()

if __name__ == "__main__":
    main()
