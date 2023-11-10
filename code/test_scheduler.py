"""Unit tests for the Scheduler class."""
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import unittest
from unittest.mock import patch

from config.pin import CURRENT_PIN
from experiment_class import ExperimentBase, ExperimentStatus, ExperimentResult
from scheduler import Scheduler

# define constants or globals
PATH_TO_CONFIG = "code/config/mill_config.json"
PATH_TO_STATUS = "code/system state"
PATH_TO_QUEUE = "code/system state/queue.csv"
PATH_TO_EXPERIMENT_INBOX = "code/experiments_inbox"
PATH_TO_EXPERIMENT_QUEUE = "code/experiment_queue"
PATH_TO_COMPLETED_EXPERIMENTS = "code/experiments_completed"
PATH_TO_ERRORED_EXPERIMENTS = "code/experiments_error"


class TestScheduler(unittest.TestCase):
    """
    A class for testing the Scheduler class.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.scheduler = Scheduler()

    def test_remove_from_queue(self):
        """
        Test the remove_from_queue method of the Scheduler class.
        """
        # Create a sample queue file
        queue_file = Path.cwd() / "test_queue.csv"
        queue_data = {
            "id": [1, 2, 3],
            "priority": [1, 2, 3],
            "filename": ["file1", "file2", "file3"],
        }
        queue_df = pd.DataFrame(queue_data)
        queue_df.to_csv(queue_file, index=False)

        # Create a sample experiment
        experiment = ExperimentBase(
            2,
            "unittests",
            2,
            "B2",
            CURRENT_PIN,
            3,
            {"water": 100},
            "new",
            "unittests_2",
        )

        # Call the remove_from_queue method
        scheduler = Scheduler()
        scheduler.remove_from_queue(experiment)

        # Check that the experiment was removed from the queue file
        expected_queue_data = {
            "id": [1, 3],
            "priority": [1, 3],
            "filename": ["file1", "file3"],
        }
        expected_queue_df = pd.DataFrame(expected_queue_data)
        expected_queue_df.to_csv(queue_file, index=False)

        with open(queue_file, "r", encoding="utf-8") as f:
            actual_data = f.read()

        with open("expected_queue.csv", "r", encoding="utf-8") as f:
            expected_data = f.read()

        assert actual_data == expected_data

    def test_check_well_status(self):
        """
        Test the check_well_status method of the Scheduler class.
        """
        # Test that the method returns the correct status for a well that exists in the file
        well_status = self.scheduler.check_well_status("A1")
        self.assertEqual(well_status, "new")

        # Test that the method returns None for a well that does not exist in the file
        well_status = self.scheduler.check_well_status("Z99")
        self.assertIsNone(well_status)

    def test_choose_alternative_well(self):
        """
        Test the choose_alternative_well method of the Scheduler class.
        """
        # Test that the method returns a well that is available
        well = self.scheduler.choose_alternative_well()
        self.assertIsNotNone(well)

        # Test that the method returns None if no wells are available
        for i in range(96):
            self.scheduler.change_well_status(f"A{i+1}", "queued")
        well = self.scheduler.choose_alternative_well()
        self.assertIsNone(well)

    def test_change_well_status(self):
        """
        Test the change_well_status method of the Scheduler class.
        """
        # Test that the method changes the status of a well in the file
        self.scheduler.change_well_status("A1", "queued")
        well_status = self.scheduler.check_well_status("A1")
        self.assertEqual(well_status, "queued")

    def test_read_new_experiments(self):
        """
        Test the read_new_experiments method of the Scheduler class.
        """
        # Test that the method reads a file and adds experiments to the queue
        experiments_read, complete = self.scheduler.read_new_experiments(
            "test_experiment"
        )
        self.assertEqual(experiments_read, 1)
        self.assertTrue(complete)

    def test_check_inbox(self):
        """
        Test the check_inbox method of the Scheduler class.
        """
        # Test that the method reads all files in the inbox folder and adds experiments to the queue
        count, complete = self.scheduler.check_inbox()
        self.assertGreater(count, 0)
        self.assertTrue(complete)

    def test_read_next_experiment_from_queue(self):
        """
        Test the read_next_experiment_from_queue method of the Scheduler class.
        """
        # Test that the method reads the next experiment from the queue
        experiment, file_path = self.scheduler.read_next_experiment_from_queue()
        self.assertIsNotNone(experiment)
        self.assertIsNotNone(file_path)

    def test_add_to_queue_file(self):
        """
        Test the add_to_queue_file method of the Scheduler class.
        """
        # Create a sample experiment
        experiment = ExperimentBase(
            4, "unitetest4", 2, "B2", CURRENT_PIN, 3, {"water": 100}, "new", "file4"
        )

        # Call the add_to_queue_file method
        scheduler = Scheduler()
        scheduler.add_to_queue_file(experiment)

        # Check that the experiment was added to the queue file
        queue_file = Path.cwd() / PATH_TO_QUEUE
        expected_queue_data = {
            "id": [1, 2, 3, 4],
            "priority": [1, 2, 3, 2],
            "filename": ["file1", "file2", "file3", "file4"],
        }
        expected_queue_df = pd.DataFrame(expected_queue_data)
        expected_queue_df.to_csv(queue_file, index=False)

        with open(queue_file, "r", encoding='utf-8') as f:
            actual_data = f.read()

        with open("expected_queue.csv", "r", encoding='utf-8') as f:
            expected_data = f.read()

        assert actual_data == expected_data
        assert experiment.status == ExperimentStatus.QUEUED

    def test_update_experiment_queue_priority(self):
        # Create a sample queue file
        queue_file = Path.cwd() / "test_queue.csv"
        queue_data = {"id": [1, 2, 3], "priority": [1, 2, 3], "filename": ["file1", "file2", "file3"]}
        queue_df = pd.DataFrame(queue_data)
        queue_df.to_csv(queue_file, index=False)

        # Call the update_experiment_queue_priority method
        experiment_id = 2
        priority = 5
        self.scheduler.update_experiment_queue_priority(experiment_id, priority)

        # Check that the priority was updated in the queue file
        expected_queue_data = {"id": [1, 2, 3], "priority": [1, 5, 3], "filename": ["file1", "file2", "file3"]}
        expected_queue_df = pd.DataFrame(expected_queue_data)
        expected_queue_df.to_csv(queue_file, index=False)

        with open(queue_file, "r", encoding="utf-8") as f:
            actual_data = f.read()

        with open("expected_queue.csv", "r", encoding="utf-8") as f:
            expected_data = f.read()

        assert actual_data == expected_data

    def test_update_experiment_status(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1")

        # Create a sample experiment file
        experiment_file = Path.cwd() / "test_experiment.json"
        with open(experiment_file, "w", encoding="UTF-8") as file:
            serialized_data = json.dumps(experiment)
            file.write(serialized_data)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = serialized_data

            # Call the update_experiment_status method
            self.scheduler.update_experiment_status(experiment)

            # Check that the status was updated in the experiment file
            expected_status = ExperimentStatus.QUEUED
            expected_status_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            expected_data = json.dumps(experiment._replace(status=str(expected_status.value), status_date=expected_status_date))
            with open(experiment_file, "r", encoding="UTF-8") as f:
                actual_data = f.read()

            assert actual_data == expected_data

    def test_update_experiment_location(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "complete", "unittests_1")

        # Create a sample experiment file
        experiment_file = Path.cwd() / "test_experiment.json"
        with open(experiment_file, "w", encoding="UTF-8") as file:
            serialized_data = json.dumps(experiment)
            file.write(serialized_data)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = serialized_data

            # Call the update_experiment_location method
            self.scheduler.update_experiment_location(experiment)

            # Check that the file was moved to the completed experiments folder
            expected_completed_file = Path.cwd() / PATH_TO_COMPLETED_EXPERIMENTS / "test_experiment.json"
            assert expected_completed_file.exists()

    def test_add_nonfile_experiment(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1")

        with patch("scheduler.Scheduler.add_to_queue_folder") as mock_add_to_queue_folder:
            with patch("scheduler.Scheduler.add_to_queue_file") as mock_add_to_queue_file:
                # Call the add_nonfile_experiment method
                result = self.scheduler.add_nonfile_experiment(experiment)

                # Check that the experiment was added to the queue folder and file
                mock_add_to_queue_folder.assert_called_once_with(experiment)
                mock_add_to_queue_file.assert_called_once_with(experiment)

                assert result == "success"

    def test_add_to_queue_folder(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1")

        # Call the add_to_queue_folder method
        result = self.scheduler.add_to_queue_folder(experiment)

        # Check that the experiment file was created in the experiment_queue folder
        expected_file_path = Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / "unittests_1.json"
        assert expected_file_path.exists()

        assert result == experiment

    def test_add_to_queue_file(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1")

        # Create a sample queue file
        queue_file = Path.cwd() / "test_queue.csv"
        queue_data = {"id": [1], "priority": [1], "filename": ["unittests_1"]}
        queue_df = pd.DataFrame(queue_data)
        queue_df.to_csv(queue_file, index=False)

        # Call the add_to_queue_file method
        result = self.scheduler.add_to_queue_file(experiment)

        # Check that the experiment was added to the queue file
        expected_queue_data = {"id": [1, 1], "priority": [1, 1], "filename": ["unittests_1", "unittests_1"]}
        expected_queue_df = pd.DataFrame(expected_queue_data)
        expected_queue_df.to_csv(queue_file, index=False)

        with open(queue_file, "r", encoding="utf-8") as f:
            actual_data = f.read()

        with open("expected_queue.csv", "r", encoding="utf-8") as f:
            expected_data = f.read()

        assert actual_data == expected_data
        assert result == experiment

    def test_add_nonfile_experiments(self):
        # Create a list of sample experiments
        experiments = [
            ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1"),
            ExperimentBase(2, "unittests", 2, "A2", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_2"),
        ]

        with patch("scheduler.Scheduler.add_nonfile_experiment") as mock_add_nonfile_experiment:
            # Call the add_nonfile_experiments method
            result = self.scheduler.add_nonfile_experiments(experiments)

            # Check that the add_nonfile_experiment method was called for each experiment
            mock_add_nonfile_experiment.assert_called_once_with(experiments[0])
            assert result == "success"

    def test_save_results(self):
        # Create a sample experiment
        experiment = ExperimentBase(1, "unittests", 1, "A1", CURRENT_PIN, 3, {"water": 100}, "new", "unittests_1")

        # Create a sample results
        results = ExperimentResult({"result": "success"})

        # Call the save_results method
        self.scheduler.save_results(experiment, results)

        # Check that the results file was saved in the data folder
        expected_results_file = Path.cwd() / "data" / "1.json"
        assert expected_results_file.exists()

if __name__ == "__main__":
    unittest.main()
