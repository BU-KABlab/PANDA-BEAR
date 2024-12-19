"""
This module is the primary module for the server loop. It is responsible for
listening for incoming connections and creating a new thread for each
connection. The thread is responsible for handling the connection.

The server is also responsible for handling the instrument's hardware connections,
labware state/status, running any optional programs like the slack_monitor, or OBS.

The server will accept a set list of actions from the client, and will respond
by performing the requested action. The server will also send updates to the client
regarding the status of the instrument, labware, and any other relevant information.
"""

# Standard library imports
from multiprocessing import Process, Queue
from threading import Thread, Event

# Third party imports

# Local imports

# Constants

# Classes

# Functions


# Main
from panda_lib.instrument_toolkit import Hardware, Labware
from panda_lib.errors import *
from panda_lib.sql_tools import sql_queue
from panda_lib.obs_controls import OBSController, OBSerror

def run():
    exp_loop_prcss: Process = None
    exp_loop_status = None
    exp_loop_queue: Queue = Queue()
    exp_cmd_queue: Queue = Queue()
    status_queue: Queue = Queue()
    slackbot_thread: Thread = None
    slackThread_running = Event()

    instruments = Hardware()
    labware = Labware()
    slack_monitor = None
    obs = None    

    # Start the server loop
    while True:
        # Check for any incoming connections
        # If a connection is found, create a new thread to handle it
        # The thread will be responsible for handling the connection
        # The server will continue to listen for new connections
        

        # Check the status of the experiment loop
        if exp_loop_prcss is None or not exp_loop_prcss.is_alive():
            exp_loop_status = "Stopped"
        else:
            exp_loop_status = "Running"

        # Check the status of the slack monitor
        if slackbot_thread is None or not slackbot_thread.is_alive():
            slackThread_running.clear()
        else:
            slackThread_running.set()

        # Check the status of the OBS connection
        # If the OBS connection is not active, try to reconnect
        if obs is None:
            try:
                obs = OBSController()
            except OBSerror.OBSSDKRequestError as e:
                obs = None


            

