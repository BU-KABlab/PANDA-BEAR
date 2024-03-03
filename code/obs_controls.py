"""
This file simplifies controlling the OBS software in the ways that we need. 
It is used to place the experiment information on the screen and to turn on and off the webcam.
"""

import logging
import time

import obsws_python as obsws
from obsws_python import error as OBSerror
from config.config import PATH_TO_LOGS, TESTING
from config.secrets import OBS_Secrets
from experiment_class import ExperimentBase, ExperimentStatus
from log_tools import e_panda_logger as logger

## set up logging to log to both the obs_control.log file and the ePANDA.log file
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler(PATH_TO_LOGS / "obs_control.log")
# system_handler = logging.FileHandler("ePANDA.log")
file_handler.setFormatter(formatter)
# system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# logger.addHandler(system_handler)


class OBSController:
    """This class is used simplify the control the OBS software for our needs"""

    def __init__(
        self,
        client_host=OBS_Secrets.HOST,
        client_password=OBS_Secrets.PASSWORD,
        client_port=OBS_Secrets.PORT,
        client_timeout=3,
    ):
        if TESTING:
            self.client = MockOBSController()
        else:
            self.client = obsws.ReqClient(
                host=client_host,
                port=client_port,
                password=client_password,
                timeout=client_timeout,
            )
            self.logger = logging.getLogger(__name__)

    def place_experiment_on_screen(self, instructions: ExperimentBase):
        """Place the experiment information on the screen"""
        try:
            exp_id = instructions.id if instructions.id else "None"
            project_id = instructions.project_id if instructions.project_id else "None"
            well_id = instructions.well_id if instructions.well_id else "None"
            status = instructions.status if instructions.status else "None"
            campaign_id = (
                instructions.project_campaign_id
                if instructions.project_campaign_id
                else 0
            )

            video_information = f"""Experiment Info:
ID: {project_id}.{campaign_id}.{exp_id}
Status: {status.value}
Well: {well_id}"""
            label = self.client.get_input_settings("text")
            label.input_settings["text"] = video_information
            # label.input_settings["font"]["size"]=240
            self.client.set_input_settings("text", label.input_settings, True)
            self.logger.info("Experiment information placed on screen.")
        except OBSerror.OBSSDKRequestError as e:
            self.logger.error("Error placing experiment information on screen: %s", e)

    def place_text_on_screen(self, text: str = None):
        """Place the given text on the screen"""
        try:
            if not text:
                text = ""
            label = self.client.get_input_settings("text")
            label.input_settings["text"] = text
            # label.input_settings["font"]["size"]=240
            self.client.set_input_settings("text", label.input_settings, True)
            self.logger.info("Text placed on screen.")
        except Exception as e:
            self.logger.error("Error placing text on screen: %s", e)

    def webcam_on(self):
        """Turn on the webcam"""
        webcam = self.client.get_input_settings("Webcam")
        webcam.input_settings["sceneItemEnabled"] = True
        self.client.set_input_settings("Webcam", webcam.input_settings, True)
        self.logger.info("Webcam turned on.")

    def webcam_off(self):
        """Turn off the webcam"""
        webcam = self.client.get_input_settings("Webcam")
        webcam.input_settings["sceneItemEnabled"] = False
        self.client.set_input_settings("Webcam", webcam.input_settings, True)
        self.logger.info("Webcam turned off.")

    def start_streaming(self):
        """Start the streaming"""
        self.client.start_stream()
        self.logger.info("Streaming started.")

    def stop_streaming(self):
        """Stop the streaming"""
        self.client.stop_stream()
        self.logger.info("Streaming stopped.")

    def start_recording(self):
        """Start the recording"""
        try:

            self.client.start_record()
            self.logger.info("Recording started.")
        except Exception as e:
            self.logger.error("Error starting recording: %s", e)

    def stop_recording(self):
        """Stop the recording"""
        try:
            self.client.stop_record()
            self.logger.info("Recording stopped.")
        except Exception as e:
            self.logger.error("Error stopping recording: %s", e)

    def set_recording_file_name(self, file_name: str):
        """Set the recording file name"""
        record_directory = self.client.get_record_directory()
        return record_directory.record_directory
        # record_name = self.client.get_recor


class MockOBSController:
    """This class is used to mock the OBS software for testing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def place_experiment_on_screen(self, instructions: ExperimentBase):
        """Place the experiment information on the screen"""
        pass

    def place_text_on_screen(self, text: str = None):
        """Place the given text on the screen"""
        pass

    def webcam_on(self):
        """Turn on the webcam"""
        pass

    def webcam_off(self):
        """Turn off the webcam"""
        pass

    def start_streaming(self):
        """Start the streaming"""
        pass

    def stop_streaming(self):
        """Stop the streaming"""
        pass

    def start_recording(self):
        """Start the recording"""
        pass

    def stop_recording(self):
        """Stop the recording"""
        pass

    def set_recording_file_name(self, file_name: str):
        """Set the recording file name"""
        pass


if __name__ == "__main__":
    exp = ExperimentBase(id=1, status=ExperimentStatus.QUEUED, well_id="A1")
    obs = OBSController()
    obs.place_experiment_on_screen(exp)
    obs.start_recording()
    time.sleep(15)
    obs.stop_recording()
