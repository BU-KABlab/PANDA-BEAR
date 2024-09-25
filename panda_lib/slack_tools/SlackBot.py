"""sendSlackMessages.py"""

# pylint: disable=line-too-long

import base64
import configparser
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from math import fabs
import threading

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from panda_lib.config.config_tools import read_testing_config
import panda_lib.experiment_class as exp
from panda_lib import vials
from panda_lib.image_tools import add_data_zone
from panda_lib.obs_controls import OBSController
from panda_lib.sql_tools import (
    sql_queue,
    sql_system_state,
    sql_wellplate,
)
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import SlackTickets
from panda_lib.wellplate import Well, Wellplate, WellCoordinates

# Create a lock for thread safety
plot_lock = threading.Lock()

 # Initialize the configparser
config = configparser.ConfigParser()

# Read the configuration file
config.read("panda_lib/config/panda_sdl_config.ini")

# Access the SLACK section
slack_config = config["SLACK"]
config_options = config["OPTIONS"]

@dataclass
class SlackCred:
    """This class is used to store the slack secrets"""
    # Assign the values from the configuration file
    TOKEN = slack_config.get("slack_token")
    DATA_CHANNEL_ID = slack_config.get("slack_data_channel_id")
    TEST_DATA_CHANNEL_ID = slack_config.get("slack_test_data_channel_id")
    CONVERSATION_CHANNEL_ID = slack_config.get("slack_conversation_channel_id")
    TEST_CONVERSATION_CHANNEL_ID = slack_config.get("slack_test_conversation_channel_id")
    ALERT_CHANNEL_ID = slack_config.get("slack_alert_channel_id")
    TEST_ALERT_CHANNEL_ID = slack_config.get("slack_test_alert_channel_id")

class Cameras(Enum):
    """
    Enum for camera types
    """
    WEBCAM = 0
    VIALS = 1
    PSTAT = 2


# region Slack Tickets
@dataclass
class SlackTicket:
    """Class for storing slack tickets."""

    msg_id: str
    channel_id: str
    msg_text: str
    valid_cmd: int
    timestamp: str
    addressed_timestamp: str


def insert_slack_ticket(ticket: SlackTicket, test: bool = False) -> None:
    """
    Insert a slack ticket into the slack_tickets table.

    Args:
        ticket (SlackTicket): The slack ticket to insert.
    """
    if config_options.getboolean("use_slack"):
        test = True
    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     INSERT INTO slack_tickets (
    #         msg_id,
    #         channel_id,
    #         message,
    #         response,
    #         timestamp,
    #         addressed_timestamp
    #         )
    #     VALUES (?, ?, ?, ?, ?, ?)
    #     """,
    #     (
    #         ticket.msg_id,
    #         ticket.channel_id,
    #         ticket.msg_text,
    #         ticket.valid_cmd,
    #         ticket.timestamp,
    #         ticket.addressed_timestamp,
    #     ),
    # )

    with SessionLocal() as session:
        session.add(
            SlackTickets(
                msg_id=ticket.msg_id,
                channel_id=ticket.channel_id,
                message=ticket.msg_text,
                response=ticket.valid_cmd,
                timestamp=ticket.timestamp,
                addressed_timestamp=ticket.addressed_timestamp,
            )
        )
        session.commit()


def select_slack_ticket(msg_id: str, test: bool = False) -> SlackTicket:
    """
    Select a slack ticket from the slack_tickets table.

    Args:
        msg_id (str): The message ID of the slack ticket.

    Returns:
        SlackTicket: The slack ticket.
    """
    if config_options.getboolean("use_slack"):
        test = True
    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT
    #         msg_id,
    #         channel_id,
    #         message,
    #         response,
    #         timestamp,
    #         addressed_timestamp
    #     FROM slack_tickets
    #     WHERE msg_id = ?
    #     """,
    #     (msg_id,),
    # ) #TODO: Replace with SQLAlchemy query

    with SessionLocal() as session:
        ticket = session.query(SlackTickets).filter(SlackTickets.msg_id == msg_id).first()
    if not ticket:
        return None
    return SlackTicket(
        msg_id=ticket.msg_id,
        channel_id=ticket.channel_id,
        msg_text=ticket.message,
        valid_cmd=ticket.response,
        timestamp=ticket.timestamp,
        addressed_timestamp=ticket.addressed_timestamp,

    )


class SlackBot:
    """Class for sending messages to Slack."""

    def __init__(self, test: bool = read_testing_config()) -> None:

        self.logger = logging.getLogger("e_panda")
        self.testing = test
        self.client = WebClient(token=SlackCred.TOKEN)
        self.auth_test_response = self.client.auth_test()

        if not self.auth_test_response["ok"]:
            self.logger.error("Slack connection failed.")
            return

        self.user_id = self.auth_test_response["user_id"]
        if not config_options.getboolean("use_slack"):
            self.testing = True

    def send_slack_message(self, channel_id: str, message) -> None:
        """Send a message to Slack."""

        # Check if slack is enabled
        if not config_options.getboolean("use_slack"):
            print(message)
            return

        client = WebClient(SlackCred.TOKEN)
        channel_id = self.channel_id(channel_id)
        if channel_id == 0 or channel_id is None:
            return

        try:
            result = client.chat_postMessage(channel=channel_id, text=message)
            print("Slack:", message)
            if result["ok"]:
                self.logger.info("Message sent:%s", message)
            else:
                self.logger.error("Error sending message:%s", message)
        except SlackApiError as error:
            self.logger.error("Error posting message: %s", error)

    def send_slack_file(self, channel: str, file, message=None) -> int:
        """Send a file to Slack."""

        # Check if slack is enabled
        if not config_options.getboolean("use_slack"):
            return

        client = WebClient(SlackCred.TOKEN)
        file = Path(file)
        filename_to_post = file.name

        channel_id = self.channel_id(channel)
        if channel_id == 0:
            return 0

        try:
            result = None
            with open(file, "rb") as f:
                result = client.files_upload_v2(
                    channel=channel_id,
                    file=f,
                    filename=filename_to_post,
                    initial_comment=message,
                )

            if result["ok"]:
                self.logger.info("File sent: %s", file.name)
                return 1
            self.logger.error("Error sending file: %s", file.name)
            return 0
        except SlackApiError as exception:
            log_msg = f"Error uploading file: {format(exception)}"
            self.logger.error(log_msg)
            return 0

    def upload_images(self, channel, images, message):
        """Upload images to Slack."""

        # Check if slack is enabled
        if not config_options.getboolean("use_slack"):
            return

        client = WebClient(SlackCred.TOKEN)
        channel_id = self.channel_id(channel)
        image_paths = [Path(image) for image in images]
        file_upload_parts = []
        for image in image_paths:
            file_upload_parts.append(
                {
                    "file": (str(image.resolve())),
                    "title": image.name,
                }
            )
        response = client.files_upload_v2(
            file_uploads=file_upload_parts,
            channel=channel_id,
            initial_comment=message,
        )

        print(response)

    def check_latest_message(self, channel: str) -> str:
        """Check Slack for the latest message."""
        if not config_options.getboolean("use_slack"):
            return
        client = WebClient(token=SlackCred.TOKEN)
        channel_id = self.channel_id(channel)
        if channel_id == 0:
            return 0

        try:
            result = client.conversations_history(
                channel=channel_id,
                limit=100,
                inclusive=True,
                # latest=datetime.now().timestamp(),
            )

            # With the 100 messages, find the most recent message that is not from the bot
            conversation_history = None
            for message in result["messages"]:
                if message["user"] != self.user_id:
                    conversation_history = message["text"]

            if conversation_history is None:
                # This means the past 100 messages are from the bot, we should stop
                sql_system_state.set_system_status(
                    sql_system_state.SystemState.SHUTDOWN, "stopping ePANDA", self.testing
                )

            else:
                conversation_history = result["messages"][0]["text"]

            return conversation_history
        except SlackApiError as error:
            error_msg = f"Error creating conversation: {format(error)}"
            self.logger.error(error_msg)
            return 0

    def check_slack_messages(self, channel: str) -> int:
        """Check Slack for messages."""
        if not config_options.getboolean("use_slack"):
            return
        # WebClient insantiates a client that can call API methods
        # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
        client = WebClient(token=SlackCred.TOKEN)
        # Store conversation history
        conversation_history = []
        # ID of the channel you want to send the message to
        channel_id = self.channel_id(channel)
        if channel_id == 0:
            return 0

        # latestTS = datetime.now().timestamp()

        try:
            self.logger.info("Checking for new messages.")
            # Call the conversations.history method using the WebClient
            # conversations.history returns the first 100 messages by default
            # These results are paginated, see:
            # https://api.slack.com/methods/conversations.history$pagination
            result = client.conversations_history(
                channel=channel_id,
                limit=1,
                inclusive=True,
                latest=datetime.now().timestamp(),
            )

            conversation_history = result["messages"]

            conversation_history2 = [
                x
                for x in conversation_history
                if (str(x["text"][0:7]).lower() == "!epanda")
            ]

            for _, payload in enumerate(conversation_history2):
                msg_id = payload["client_msg_id"]
                msg_text: str = payload["text"]
                msg_ts = payload["ts"]
                lookup_tickets = self.find_id(msg_id)
                if lookup_tickets is False:
                    # Send message to Slack
                    logging.info("New message found: %s", msg_text)
                    response = self.parse_slack_message(
                        msg_text[8:].rstrip(), channel_id
                    )

                    insert_slack_ticket(
                        SlackTicket(
                            msg_id=msg_id,
                            channel_id=channel_id,
                            msg_text=msg_text,
                            valid_cmd=response,
                            timestamp=msg_ts,
                            addressed_timestamp=datetime.now().timestamp(),
                        ),
                        test=self.testing,
                    )

                    if response == 0:
                        return 0
                    else:
                        print(f"responded to {msg_id}")
                        return 1
                else:
                    continue

            return 1

        except SlackApiError as error:
            error_msg = f"Error creating conversation: {format(error)}"
            self.logger.error(error_msg)
            return 0

    def find_id(self, msg_id):
        """Find the message ID in the slack ticket tracker csv file."""
        ticket = select_slack_ticket(msg_id, test=self.testing)
        if ticket is not None:
            return ticket
        return False

    def parse_slack_message(self, text: str, channel_id) -> int:
        """
        Parse the Slack message for commands.
        If command is valid, execute command and returns 0 else return 1.

        Valid commands: help, plot experiment #, share experiment #, status experiment #, vial status, well status, pause, resume, start, stop

        Args:
            message (str): The message to parse without the bot keyword !epanda.

        Returns:
            1 if command is valid, 0 if command is invalid.
        """
        # clean inputs
        text = text.lower()

        # Parse message
        if text == "help":
            self.__help_menu(channel_id=channel_id)
            return 1

        elif text[0:15] == "data experiment":
            # Get experiment number.
            # experiment_number = text[7:]
            return 1

        elif (
            text[0:17] == "status-experiment"
            or text[0:17] == "status experiment"
            or text[0:17] == "experiment status"
        ):
            # Get experiment number
            try:
                experiment_number = int(text[17:].strip())
                # Get status
                status = exp.select_experiment_status(experiment_number)
                message = f"The status of experiment {experiment_number} is {status}."
                self.send_slack_message(channel_id, message)
            except ValueError:
                message = "Please enter a valid experiment number."
                self.send_slack_message(channel_id, message)
            return 1

        elif text[0:17] == "images experiment":
            # Get experiment number
            try:
                experiment_number = int(text[17:].strip())
                self.__share_experiment_images(experiment_number)

            except ValueError:
                message = "Please enter a valid experiment number."
                self.send_slack_message(channel_id, message)
            return 1
        elif text[0:11] == "vial status":
            self.__vial_status(channel_id=channel_id)
            return 1

        elif text[0:11] == "well status":
            # Get well status
            self.__well_status(channel_id=channel_id)
            return 1

        elif text[0:12] == "queue length":
            self.__queue_length(channel_id=channel_id)
            return 1
        elif text[0:13] == "system status":
            self.__queue_length(channel_id=channel_id)
            self.__well_status(channel_id=channel_id)
            time.sleep(1)
            self.__vial_status(channel_id=channel_id)
            return 1

        elif text[0:10] == "screenshot":
            try:
                parts = text.split("-")
                camera = parts[1].strip().lower()
                # # Validate the camera choice against the Cameras enum
                # try:
                #     camera = Cameras[camera.upper()]
                # except KeyError:
                #     message = "Please specify a valid camera to take a screenshot of."
                #     self.send_slack_message(channel_id, message)
                #     message = "Valid cameras are: webcam, vials, pstat"
                #     self.send_slack_message(channel_id, message)
                #     return 1

                self.take_screenshot(channel_id, camera)
            except IndexError:
                message = (
                    "Please specify which camera to take a screenshot of with a '-'."
                )
                self.send_slack_message(channel_id, message)
            return 1

        elif text[0:7] == "status":
            sql_system_state.select_system_status()
        elif text[0:5] == "pause":
            sql_system_state.set_system_status(
                sql_system_state.SystemState.PAUSE, "pausing ePANDA", self.testing
            )
            return 1

        elif text[0:6] == "resume":
            sql_system_state.set_system_status(
                sql_system_state.SystemState.RESUME, "resuming ePANDA", self.testing
            )
            return 1

        elif text[0:5] == "start":
            # system_state.set_system_status(system_state.SystemState.ON, "starting ePANDA", self.test)
            # start the experiment loop
            # controller.main()
            self.send_slack_message(
                channel_id, "Sorry starting the ePANDA is not something I can do yet"
            )
            return 1

        elif text[0:4] == "shutdown":
            sql_system_state.set_system_status(
                sql_system_state.SystemState.SHUTDOWN, "stopping ePANDA", self.testing
            )
            return 1

        elif text[0:4] == "stop":
            return 0

        elif text[0:4] == "exit":
            return 0

        else:
            message = "Sorry, I don't understand that command. Type !epanda help for commands I understand."
            self.send_slack_message(channel_id, message)
            return 1

    def __help_menu(self, channel_id):
        """Sends the help menu to the user."""

        if channel_id != SlackCred.DATA_CHANNEL_ID:
            message = (
                "Here is a list of commands I understand:\n"
                "help -> displays this message\n"
                # "plot experiment # - plots plots the CV data for experiment #\n"
                # "data experiment # - sends the data files for experiment #\n"
                "status experiment # -> displays the status of experiment #\n"
                "vial status -> displays the status of the vials\n"
                "well status -> displays the status of the wells and the rest of the deck\n"
                "queue length -> displays the length of the queue\n"
                "status -> displays the status of the vials, wells, and queue\n"
                "screenshot-{camera name} -> takes a screenshot of the specified camera\n"
                "pause -> pauses the experiment loop\n"
                "resume -> resumes the experiment loop\n"
                # "start - starts the experiment loop\n"
                "shutdown -> stops the experiment loop and the main menu\n"
                "stop -> stops the monitoring loop\n"
                "exit -> closes the slackbot\n"
            )
        else:  # data channel
            message = (
                "Here is a list of commands I understand:\n"
                "help -> displays this message\n"
                # "plot experiment # - plots plots the CV data for experiment #\n"
                # "data experiment # - sends the data files for experiment #\n"
                "images experiment # -> sends the images for experiment #\n"
                "status experiment # -> displays the status of experiment #\n"
                "vial status -> displays the status of the vials\n"
                "well status -> displays the status of the wells and the rest of the deck\n"
                "queue length -> displays the length of the queue\n"
                "status -> displays the status of the vials, wells, and queue\n"
                "screenshot-{camera name} -> takes a screenshot of the specified camera\n"
                "pause -> pauses the experiment loop\n"
                "resume -> resumes the experiment loop\n"
                # "start - starts the experiment loop\n"
                "shutdown -> stops the experiment loop and the main menu\n"
                "stop -> stops the monitoring loop\n"
            )
        self.send_slack_message(channel_id, message)
        return 1

    def __vial_status(self, channel_id):
        """Sends the vial status to the user."""
        # Get vial status
        # ## Load the vial status json file
        # stock_vials = pd.read_json(STOCK_STATUS)
        # ## Filter for just the vial position and volume
        # stock_vials = stock_vials[["position", "volume", "name", "contents"]]
        # # Drop any vials that have null values
        # stock_vials = stock_vials.dropna()
        # ## set position to be a string and volume to be a float
        # stock_vials["position"] = stock_vials["position"].astype(str)
        # stock_vials["volume"] = stock_vials["volume"].astype(float)

        stock_status, waste_status = vial_status()
        self.send_slack_file(channel=channel_id, file=stock_status)
        self.send_slack_file(channel=channel_id, file=waste_status)
        Path(stock_status).unlink()
        Path(waste_status).unlink()


    def __well_status(self, channel_id):
        """Sends the well status to the user."""
        file_path_for_plot = well_status()
        self.upload_images(channel_id, [file_path_for_plot.absolute()], "Well Status")
        file_path_for_plot.unlink()
        return 1

    def __queue_length(self, channel_id):
        # Get queue length
        message = f"The queue length is {sql_queue.count_queue_length()}."
        self.send_slack_message(channel_id, message)
        return 1

    def _get_well_color(self, status: str) -> str:
        """Get the color of a well based on its status."""
        if status is None:
            return "black"
        color_mapping = {
            "empty": "black",
            "new": "grey",
            "queued": "orange",
            "complete": "green",
            "error": "red",
            "paused": "blue",
        }
        return color_mapping.get(status, "purple")

    def take_screenshot(self, channel_id, camera_name: str):
        """Take a screenshot of the camera."""
        if not config_options.getboolean("use_obs"):
            self.send_slack_message(channel_id, "OBS is not enabled")
            return 1
        try:
            file_name = "tmp_screenshot.png"
            obs = OBSController()
            # verify that the camera is an active source
            try:
                sources = obs.client.get_source_active(camera_name)
            except Exception:
                self.send_slack_message(
                    channel_id, f"Could not find a camera source named {camera_name}"
                )
                return 1
            if not sources:
                self.send_slack_message(
                    channel_id, f"Camera {camera_name} is not active"
                )
                return 1
            screenshot = obs.client.get_source_screenshot(
                camera_name, "png", 1920, 1080, -1
            )
            img = Image.open(
                BytesIO(base64.b64decode(screenshot.image_data.split(",")[1]))
            )
            img = add_data_zone(img, context=f"{camera_name.capitalize()} Screenshot")
            img.save(file_name, "png")
            self.send_slack_file(
                channel_id, file_name, f"{camera_name.capitalize()} Screenshot"
            )
            Path(file_name).unlink()  # delete the file
            return 1

        except Exception as e:
            self.send_slack_message(channel_id, "Error taking screenshot")
            self.send_slack_message(channel_id, str(e))
            return 1

    def __share_experiment_images(self, experiment_id: int):
        """Share the images for an experiment."""
        # Look up there experiment_id in the db and find all results of type image
        # Then filter the results to only include those with dz in the name
        # Then send the images to slack

        results = exp.select_specific_result(experiment_id, "image")
        if results == [] or results is None:
            message = f"Experiment {experiment_id} does not have any images. Or the experiment {experiment_id} does not exist."
            self.send_slack_message("data", message)
            return
        for result in results:
            result: exp.ExperimentResultsRecord
            if "dz" not in result.result_value:
                results.remove(result)

        # Now make a list of the image paths
        image_paths = [result.result_value for result in results]

        # Now send the images to slack
        self.upload_images(
            "data", image_paths, f"Images for experiment {experiment_id}"
        )

    def channel_id(self, channel: str) -> str:
        """Return the channel ID based on the channel name."""
        if channel == "conversation":
            channel_id = (
                SlackCred.CONVERSATION_CHANNEL_ID
                if not self.testing
                else SlackCred.TEST_ALERT_CHANNEL_ID
            )
        elif channel == "alert":
            channel_id = (
                SlackCred.ALERT_CHANNEL_ID
                if not self.testing
                else SlackCred.TEST_ALERT_CHANNEL_ID
            )
        elif channel == "data":
            channel_id = (
                SlackCred.DATA_CHANNEL_ID
                if not self.testing
                else SlackCred.TEST_DATA_CHANNEL_ID
            )
        elif channel in [
            SlackCred.CONVERSATION_CHANNEL_ID,
            SlackCred.ALERT_CHANNEL_ID,
            SlackCred.DATA_CHANNEL_ID,
            SlackCred.TEST_ALERT_CHANNEL_ID,
            SlackCred.TEST_DATA_CHANNEL_ID,
            SlackCred.TEST_CONVERSATION_CHANNEL_ID,
        ]:
            channel_id = channel
        else:
            return 0
        return channel_id

    def run(self):
        """Run the slack bot."""
        self.status = 1
        self.send_slack_message("alert", "PANDA Bot is monitoring Slack")
        while self.status == 1:
            try:
                time.sleep(5)
                self.status = self.check_slack_messages(channel="alert")
                self.check_slack_messages(channel="data")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
                time.sleep(15)
                continue
        self.send_slack_message("alert", "PANDA Bot is off duty")
        print("Stopping Slack Bot")



def vial_status(vial_type: Union[str, None] = None) -> tuple[Path, Path]:
    """
    Create plots of the vial status' and return the file paths.
    """
    # Get vial status
    # ## Load the vial status json file
    # stock_vials = pd.read_json(STOCK_STATUS)
    # ## Filter for just the vial position and volume
    # stock_vials = stock_vials[["position", "volume", "name", "contents"]]
    # # Drop any vials that have null values
    # stock_vials = stock_vials.dropna()
    # ## set position to be a string and volume to be a float
    # stock_vials["position"] = stock_vials["position"].astype(str)
    # stock_vials["volume"] = stock_vials["volume"].astype(float)
    spacing = 1
    stock_vials = vials.get_current_vials("stock")  # returns a list of Vial objects
    stock_vials = pd.DataFrame([vial for vial in stock_vials])
    stock_vials = stock_vials[["position", "volume", "name", "contents"]]
    stock_vials = stock_vials.dropna()
    stock_vials["position"] = stock_vials["position"].astype(str)
    stock_vials["volume"] = stock_vials["volume"].astype(float)

    # Create new x-coordinates with spacing
    x_positions = range(len(stock_vials["position"]))
    x_positions_spaced = [x * spacing for x in x_positions]

    ## Create a bar graph with volume on the x-axis and position on the y-axis
    ## Send the graph to slack
    with plot_lock:
    
        plt.bar(
            #x_positions_spaced,
            stock_vials["position"],
            stock_vials["volume"],
            align="center",
            alpha=0.5,
            color="blue",
            #width=1.0,
        )
        # label each bar with the volume
        for i, v in enumerate(stock_vials["volume"]):
            plt.text(i*spacing, v, str(round(v, 2)), color="black", ha="center", bbox=dict(facecolor='white', edgecolor='none', pad=1), fontsize = 10)

        # Draw a horizontal line at 4000
        plt.axhline(y=2000, color="red", linestyle="-")
        # Write the name of the vial vertically in the bar
        for i, v in enumerate(stock_vials["contents"]):
            plt.text(i*spacing, 1000, str(v), color="black", ha="center", rotation=90)
        plt.xlabel("Position")
        plt.ylabel("Volume")
        plt.title("Stock Vial Status")

        filepath_stock = Path("vial_status.png")
        plt.savefig(filepath_stock, format="png")
        plt.close()

        # And the same for the waste vials
        # waste_vials = pd.read_json(WASTE_STATUS)
        waste_vials = vials.get_current_vials("waste")
        waste_vials = pd.DataFrame([vial for vial in waste_vials])
        waste_vials = waste_vials[["position", "volume", "name"]]
        # Drop any vials that have null values
        waste_vials = waste_vials.dropna()
        waste_vials["position"] = waste_vials["position"].astype(str)
        waste_vials["volume"] = waste_vials["volume"].astype(float)

        # Create new x-coordinates with spacing
        x_positions = range(len(waste_vials["position"]))
        x_positions_spaced = [x * spacing for x in x_positions]

        plt.bar(
            #x_positions_spaced,
            waste_vials["position"],
            waste_vials["volume"],
            align="center",
            alpha=0.5,
            color="blue",
            #width = 1.0
        )
        # label each bar with the volume
        for i, v in enumerate(waste_vials["volume"]):
            plt.text(i*spacing, v, str(round(v, 2)), color="black", ha="center", bbox=dict(facecolor='white', edgecolor='none', pad=1), fontsize = 10)
        plt.axhline(y=20000, color="red", linestyle="-")

        # Write the name of the vial vertically in the bar
        for i, v in enumerate(waste_vials["name"]):
            plt.text(i*spacing, 1000, str(v), color="black", ha="center", rotation=90)
        plt.xlabel("Position")
        plt.ylabel("Volume")
        plt.title("Waste Vial Status")
        filepath_waste = Path("waste_status.png")
        plt.savefig(filepath_waste, format="png")
        plt.close()
        if vial_type == "stock":
            return filepath_stock.absolute()
        elif vial_type == "waste":
            return filepath_waste.absolute()
        else:
            return filepath_stock.absolute(), filepath_waste.absolute()

def well_status() -> Path:
    """
    Create a plot of the well status and return the file path.
    """
    # Check current wellplate type
    _, type_number, _ = sql_wellplate.select_current_wellplate_info()
    wellplate_type = sql_wellplate.select_well_characteristics(
        type_number
    )
    # Choose the correct wellplate object based on the wellplate type
    wellplate: Wellplate = None
    if wellplate_type.shape == "circular":
        wellplate = Wellplate(
            type_number=type_number,
        )
    elif wellplate_type.shape == "square":
        wellplate = Wellplate(
            type_number=type_number,
        )

    ## Well coordinates and colors
    # Plot the well plate on a coordinate plane.
    x_coordinates = []
    y_coordinates = []
    color = []

    current_wells = sql_wellplate.select_wellplate_wells()
    # turn tuple of well info into a list of well objects
    current_wells = [Well(*well) for well in current_wells]

    for well in current_wells:
        x_coordinates.append(well.coordinates["x"])
        y_coordinates.append(well.coordinates["y"])
        color.append(get_well_color(well.status))

    if wellplate.shape == "circular":
        marker = "o"
    else:
        marker = "s"

    ## Label the wellplate with the plate id below the bottom row and centered to the wellplate
    # get the coordinates of wells H12 and A12
    corners = wellplate.get_corners()
    top_right = corners["top_right"]
    bottom_right = corners["bottom_right"]
    bottom_left = corners["bottom_left"]
    top_left = corners["top_left"]

    # calculate the center of the wellplate
    center = bottom_left["x"] + (fabs(bottom_left["x"]) - fabs(bottom_right["x"])) / 2
    
    with plot_lock:
        # plot the plate id
        plt.text(
            center, bottom_left["y"] - 20, str(wellplate.plate_id), color="black", ha="center"
        )

        ## Vial coordinates
        vial_x = []
        vial_y = []
        vial_color = []
        vial_marker = []  # a circle for these circular vials
        ## Vials
        # with open(WASTE_STATUS, "r", encoding="utf-8") as stock:
        #     data = json.load(stock)
        data = vials.get_current_vials("waste")
        for vial in data:
            #vial = vial.to_dict()
            vial_x.append(vial["vial_coordinates"]["x"])
            vial_y.append(vial["vial_coordinates"]["y"])
            volume = vial["volume"]
            capacity = vial["capacity"]
            if vial["name"] is None or vial["name"] == "":
                vial_color.append("black")
                vial_marker.append("x")
            elif volume / capacity > 0.75:
                vial_color.append("red")
                vial_marker.append("o")
            elif volume / capacity > 0.50:
                vial_color.append("yellow")
                vial_marker.append("o")
            else:
                vial_color.append("green")
                vial_marker.append("o")
        # with open(STOCK_STATUS, "r", encoding="utf-8") as stock:
        #     data = json.load(stock)
        data = vials.get_current_vials("stock")
        for vial in data:
            #vial = vial.to_dict()
            vial_x.append(vial["vial_coordinates"]["x"])
            vial_y.append(vial["vial_coordinates"]["y"])
            volume = vial["volume"]
            capacity = vial["capacity"]
            if vial["name"] is None or vial["name"] == "":
                vial_color.append("black")
                vial_marker.append("x")
            elif volume / capacity > 0.5:
                vial_color.append("green")
                vial_marker.append("o")
            elif volume / capacity > 0.25:
                vial_color.append("yellow")
                vial_marker.append("o")
            else:
                vial_color.append("red")
                vial_marker.append("o")

        try:
            vial_radius = data[0]["radius"]
        except IndexError:
            vial_radius = 100

        # Draw the gasket outline
        gasket_length = wellplate.gasket_length
        gasket_width = wellplate.gasket_width
        orientation = wellplate.orientation

        if orientation == 0:
            gasket_origin = WellCoordinates(wellplate.a1_x + wellplate.a1_y_wall_offset, wellplate.a1_y + wellplate.a1_x_wall_offset,0)

            gasket_x = [
                gasket_origin.x,
                gasket_origin.x,
                gasket_origin.x - gasket_width,
                gasket_origin.x - gasket_width,
                gasket_origin.x,
            ]
            gasket_y = [
                gasket_origin.y,
                gasket_origin.y - gasket_length,
                gasket_origin.y - gasket_length,
                gasket_origin.y,
                gasket_origin.y,
            ]
        elif orientation == 1:
            gasket_origin = WellCoordinates(wellplate.a1_x - wellplate.a1_x_wall_offset, wellplate.a1_y - wellplate.a1_y_wall_offset,0)
            gasket_x = [
                gasket_origin.x,
                gasket_origin.x,
                gasket_origin.x + gasket_width,
                gasket_origin.x + gasket_width,
                gasket_origin.x,
            ]
            gasket_y = [
                gasket_origin.y,
                gasket_origin.y + gasket_length,
                gasket_origin.y + gasket_length,
                gasket_origin.y,
                gasket_origin.y,
            ]
        elif orientation == 2:
            gasket_origin = WellCoordinates(wellplate.a1_x - wellplate.a1_x_wall_offset, wellplate.a1_y + wellplate.a1_y_wall_offset,0)
            gasket_x = [
                gasket_origin.x,
                gasket_origin.x + gasket_length,
                gasket_origin.x + gasket_length,
                gasket_origin.x,
                gasket_origin.x,
            ]
            gasket_y = [
                gasket_origin.y,
                gasket_origin.y,
                gasket_origin.y - gasket_width,
                gasket_origin.y - gasket_width,
                gasket_origin.y,
            ]
        elif orientation == 3:
            gasket_origin = WellCoordinates(wellplate.a1_x + wellplate.a1_x_wall_offset, wellplate.a1_y - wellplate.a1_y_wall_offset,0)
            gasket_x = [
                gasket_origin.x,
                gasket_origin.x - gasket_length,
                gasket_origin.x - gasket_length,
                gasket_origin.x,
                gasket_origin.x,
            ]
            gasket_y = [
                gasket_origin.y,
                gasket_origin.y,
                gasket_origin.y + gasket_width,
                gasket_origin.y + gasket_width,
                gasket_origin.y,
            ]
        else:
            raise ValueError("Invalid orientation value. Must be 0, 1, 2, or 3.")

        plt.plot(gasket_x, gasket_y, c="black", lw=1.5)

        # Plot the well plate
        plt.scatter(
            x_coordinates, y_coordinates, marker=marker, c=color, s=3.14 *(wellplate.radius**2), alpha=0.5
        )
        plt.scatter(vial_x, vial_y, marker="o", c=vial_color, s=3.14 *(vial_radius**2), alpha=1)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Status of Stage Items")
        plt.grid(True, "both")
        plt.xlim(-420, 10)
        plt.ylim(-310, 10)
        file_path_for_plot = Path("well_status.png")
        plt.savefig(file_path_for_plot, format="png")
        plt.close()
        return file_path_for_plot.absolute()


def get_well_color( status: str) -> str:
    """Get the color of a well based on its status."""
    if status is None:
        return "black"
    color_mapping = {
        "empty": "black",
        "new": "grey",
        "queued": "orange",
        "complete": "green",
        "error": "red",
        "paused": "blue",
    }
    return color_mapping.get(status, "purple")

if __name__ == "__main__":
    slack_bot = SlackBot(test=False)
    TEST_MESSAGE = "This is a test message."
    EPANDA_HELLO = """Hello ePANDA team! I am ePANDA..."""
    # slack_bot.check_slack_messages("alert")
    slack_bot.send_slack_message("alert", TEST_MESSAGE)
