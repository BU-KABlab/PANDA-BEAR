"""For running test scripts in the testing directory"""
from panda_lib.testing_and_validation import(
    test_pump_control,
    test_vials,
    test_pipette,
    test_obs,
    test_wellplate_v2,
    test_scheduler
)
import unittest

if __name__ == "__main__":
    # test_pump_control.unittest.main()
    # test_vials.TestReadVials()
    # test_pipette.unittest.main()
    # test_obs.unittest.main()
    # test_wellplate_v2.unittest.main()
    # test_scheduler.unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(test_vials.TestReadVials)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_pump_control.TestSyringePump))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_pipette.TestPipette))

    # Create a test runner and run the tests
    runner = unittest.TextTestRunner()
    result = runner.run(suite)