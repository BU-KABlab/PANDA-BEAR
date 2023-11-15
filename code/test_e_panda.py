import unittest
from unittest.mock import MagicMock
from e_panda import pipette_v2
from vials import Vessel, StockVial, WasteVial
from mill_control import MockMill
from pump_control import MockPump
from wellplate import Well, Wells2
from sartorius.mock import Scale as MockScale
class TestEPanda(unittest.TestCase):
    def setUp(self):
        self.from_vessel = Vessel(name="Test Vessel 1", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0})
        self.to_vessel = Vessel(name="Test Vessel 2", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0})
        self.mill = MockMill()
        self.scale = MockScale()
        self.pump = MockPump(self.mill,self.scale)

    def test_pipette_v2(self):
        # Test pipetting from a vessel to another vessel
        self.from_vessel.volume = 50.0
        self.to_vessel.volume = 50.0
        volume = 20.0
        pipette_v2(
            volume=volume,
            from_vessel=self.from_vessel,
            to_vessel=self.to_vessel,
            pump=self.pump,
            mill=self.mill,
            pumping_rate=None,
        )
        self.assertEqual(self.from_vessel.volume, 30.0)
        self.assertEqual(self.to_vessel.volume, 70.0)

        # Test pipetting from a well to a waste vial
        self.from_vessel = Well(well_id="T1", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, height = 20, depth=10, status = "new")
        self.to_vessel = WasteVial(name="Test Waste Vial", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        self.from_vessel.volume = 50.0
        self.to_vessel.volume = 50.0
        volume = 20.0
        pipette_v2(
            volume=volume,
            from_vessel=self.from_vessel,
            to_vessel=self.to_vessel,
            pump=self.pump,
            mill=self.mill,
            pumping_rate=None,
        )
        self.assertEqual(self.from_vessel.volume, 30.0)
        self.assertEqual(self.to_vessel.volume, 70.0)

        # Test pipetting from a stock vial to a waste vial
        self.from_vessel = StockVial(name="Test Stock Vial", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        self.to_vessel = WasteVial(name="Test Waste Vial", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        self.from_vessel.volume = 50.0
        self.to_vessel.volume = 50.0
        volume = 20.0
        pipette_v2(
            volume=volume,
            from_vessel=self.from_vessel,
            to_vessel=self.to_vessel,
            pump=self.pump,
            mill=self.mill,
            pumping_rate=None,
        )
        self.assertEqual(self.from_vessel.volume, 30.0)
        self.assertEqual(self.to_vessel.volume, 70.0)

        # Test raising an error when pipetting from a well to a stock vial
        self.from_vessel = Well(well_id="T1", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, height = 20, depth=10, status = "new")
        self.to_vessel = StockVial(name="Test Stock Vial", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        with self.assertRaises(ValueError):
            pipette_v2(
                volume=20.0,
                from_vessel=self.from_vessel,
                to_vessel=self.to_vessel,
                pump=self.pump,
                mill=self.mill,
                pumping_rate=None,
            )

        # Test raising an error when pipetting from a waste vial to a well
        self.from_vessel = WasteVial(name="Test Waste Vial", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        self.to_vessel = Well(well_id="T1", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, height = 20, depth=10, status = "new")
        with self.assertRaises(ValueError):
            pipette_v2(
                volume=20.0,
                from_vessel=self.from_vessel,
                to_vessel=self.to_vessel,
                pump=self.pump,
                mill=self.mill,
                pumping_rate=None,
            )

        # Test raising an error when pipetting from a stock vial to a stock vial
        self.from_vessel = StockVial(name="Test Stock Vial 1", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        self.to_vessel = StockVial(name="Test Stock Vial 2", volume=50.0, capacity=100.0, density=1.0, coordinates={'x':0,'y':0,'z':0}, radius=5, height=10, z_bottom=0)
        with self.assertRaises(ValueError):
            pipette_v2(
                volume=20.0,
                from_vessel=self.from_vessel,
                to_vessel=self.to_vessel,
                pump=self.pump,
                mill=self.mill,
                pumping_rate=None,
            )

if __name__ == '__main__':
    unittest.main()