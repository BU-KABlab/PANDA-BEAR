# pylint: disable=line-too-long
from configparser import ConfigParser

from panda_lib.slack_tools.SlackBot import SlackBot

class Analyzer:
    """
    A demo analyzer class for the PANDA SDL
    """
    PROJECT_ID: int = 999
    config = ConfigParser()

    # Set up the ML filepaths, for this project this is hardcoded only here
    ml_file_paths:tuple = ()

    def __init__(self):
        pass

    def main(self, experiment_id: int = None, generate_experiment: bool = True)->int:
        """
        Main function for the PEDOT analyzer.

        If the system is in testing mode, the function will only generate a new experiment.
        It will not analyze the experiment.

        Args:
            experiment_id (int, optional): The experiment ID to analyze. Defaults to None.
            generate_experiment (bool, optional): Whether to generate a new experiment. Defaults to True.

        Returns:
            int: The ID of the new experiment if generate_experiment is True. Otherwise, None.

        """

        return


    def run_ml_model(self, generate_experiment_id=None) -> int:
        """
        Runs the ML model for the PEDOT experiment.

        Args:
            generate_experiment_id ([type], optional): The experiment ID to generate. Defaults to None.
        """
       
        return





    def generator(
        self, params: object, experiment_name:str="demo", campaign_id:int=0
    ) -> int:
        """Generates a PEDOT experiment."""

        return


    def analyze(self, experiment_id: int, add_to_training_data:bool=False) -> object:
        """
        Analyzes the experiment and returns the training data for the ML model.

        Args:
            experiment_id (int): The experiment ID to analyze.

        Returns:
            MLTrainingData: The training data to be used for the ML model.
        
        """
        
        return


    def share_analysis_to_slack(
        self, experiment_id: int, next_exp_id: int = None, slack: SlackBot = None
    ):
        """
        Share the analysis results with the slack data channel

        Args:
            experiment_id (int): The experiment ID to analyze
            next_exp_id (int, optional): The next experiment ID. Defaults to None.
            slack (SlackBot, optional): The slack bot. Defaults to None.
        """
        pass