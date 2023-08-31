'''
This file simplifies controlling the OBS software in the ways that we need. 
It is used to place the experiment information on the screen and to turn on and off the webcam.
'''
import logging
import obsws_python as obsws
from experiment_class import Experiment

## set up logging to log to both the obs_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("obs_control.log")
system_handler = logging.FileHandler("ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)

class OBSController():
    ''' This class is used simplify the control the OBS software for our needs'''
    def __init__(self):
        self.client = obsws.ReqClient(host='localhost', port=4455, password='PandaBear!', timeout=3)

    def place_text_on_screen(self, instructions: Experiment):
        ''' Place the experiment information on the screen'''
        video_information = f'''
            Experiment Parameters:
                Experiment ID: {instructions.id}
                Status: {instructions.status}
                Well: {instructions.target_well}
               '''
        label = self.client.get_input_settings("text")
        label.input_settings["text"]=video_information
        label.input_settings["font"]["size"]=40
        self.client.set_input_settings("text",label.input_settings,True)

    def webcam_on(self):
        ''' Turn on the webcam'''
        webcam = self.client.get_input_settings("Webcam")
        webcam.input_settings["sceneItemEnabled"]=True
        self.client.set_input_settings("Webcam",webcam.input_settings,True)

    def webcam_off(self):
        ''' Turn off the webcam'''
        webcam = self.client.get_input_settings("Webcam")
        webcam.input_settings["sceneItemEnabled"]=False
        self.client.set_input_settings("Webcam",webcam.input_settings,True)

        
