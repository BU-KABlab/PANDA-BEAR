"""sendSlackMessages.py"""

# pylint: disable=line-too-long

import configparser
import json
import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import List, Union

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from panda_lib.experiments.experiment_types import (
    ExperimentBase,
    _select_experiment_status,
)
from panda_lib.experiments.results import (
    ExperimentResultsRecord,
    select_specific_result,
)
from panda_lib.labware import vials
from panda_lib.labware.wellplates import Well
from panda_lib.sql_tools import (
    count_queue_length,
    select_current_wellplate_info,
    select_well_characteristics,
    select_wellplate_wells,
)
from panda_lib.sql_tools.queries import system
from panda_shared.config.config_tools import read_config, read_testing_config
from panda_shared.log_tools import setup_default_logger

from .sql_slack_tickets import SlackTicket, insert_slack_ticket, select_slack_ticket

# Create a lock for thread safety
plot_lock = threading.Lock()

# Initialize the configparser
config = configparser.ConfigParser()

# Read the configuration file
config = read_config()

# Access the SLACK section
slack_config = config["SLACK"]
config_options = config["OPTIONS"]


@dataclass
class IconEmojies:
    green = "🟢"
    red = "🔴"
    yellow = "🟡"
    blue = "🔵"
    black = "⚫"
    purple = "🟣"
    grey = "⚪"
    orange = "🟠"
    white = "⚪"
    empty = "⚪"
    new = "⚪"
    queued = "🟠"
    complete = "🟢"
    error = "🔴"
    paused = "🔵"
    imaging = "📷"
    rinsing = "🚿"


@dataclass
class SlackCred:
    """This class is used to store the slack secrets"""

    # Assign the values from the configuration file
    TOKEN = slack_config.get("slack_token")
    DATA_CHANNEL_ID = slack_config.get("slack_data_channel_id")
    TEST_DATA_CHANNEL_ID = slack_config.get("slack_test_data_channel_id")
    CONVERSATION_CHANNEL_ID = slack_config.get("slack_conversation_channel_id")
    TEST_CONVERSATION_CHANNEL_ID = slack_config.get(
        "slack_test_conversation_channel_id"
    )
    ALERT_CHANNEL_ID = slack_config.get("slack_alert_channel_id")
    TEST_ALERT_CHANNEL_ID = slack_config.get("slack_test_alert_channel_id")


class Cameras(Enum):
    """
    Enum for camera types
    """

    WEBCAM = 0
    VIALS = 1
    PSTAT = 2


class SlackBot:
    """Class for sending messages to Slack."""

    def __init__(self, test: bool = read_testing_config()) -> None:
        self.logger = setup_default_logger(
            "slack_bot.log", "slack_bot", logging.INFO, logging.ERROR
        )
        self.testing = test

        # If in test mode or slack is disabled, don't make real API calls
        use_slack = config_options.getboolean("use_slack") and not self.testing

        if use_slack:
            self.client = WebClient(token=SlackCred.TOKEN)
            try:
                self.auth_test_response = self.client.auth_test()
                if not self.auth_test_response["ok"]:
                    self.logger.error("Slack connection failed.")
                    self.user_id = None
                    return
                self.user_id = self.auth_test_response["user_id"]
            except SlackApiError as e:
                self.logger.error(f"Slack API Error: {e}")
                self.user_id = None
        else:
            # Create the client but it will be mocked in tests
            self.client = WebClient(token="test_token")
            self.auth_test_response = {"ok": True, "user_id": "test_user"}
            self.user_id = "test_user"
            self.logger.info(
                "Running in test mode or Slack is disabled - no real API calls will be made"
            )

        self.status = 1
        self.logger.setLevel(logging.ERROR)

    def __exit__(self, exc_type, exc_value, traceback):
        self.off_duty()

    def send_message(self, channel_id: str, message) -> None:
        """Send a message to Slack."""

        # Check if slack is enabled
        if not config_options.getboolean("use_slack"):
            # print(message)
            return

        # client = WebClient(SlackCred.TOKEN)

        channel_id = self.channel_id(channel_id)
        if channel_id == 0 or channel_id is None:
            return

        try:
            result = self.client.chat_postMessage(channel=channel_id, text=message)
            # print("Slack:", message)
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

        # client = WebClient(SlackCred.TOKEN)
        file = Path(file)
        filename_to_post = file.name

        channel_id = self.channel_id(channel)
        if channel_id == 0:
            return 0

        try:
            result = None
            with open(file, "rb") as f:
                result = self.client.files_upload_v2(
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
        _ = client.files_upload_v2(
            file_uploads=file_upload_parts,
            channel=channel_id,
            initial_comment=message,
        )

        # print(response)

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
                system.set_system_status(
                    system.SystemState.SHUTDOWN,
                    "stopping ePANDA",
                    self.testing,
                )

            else:
                conversation_history = result["messages"][0]["text"]

            return conversation_history
        except SlackApiError as error:
            error_msg = f"Error creating conversation: {format(error)}"
            self.logger.error(error_msg)

            if "rate_limited" in error_msg:
                time.sleep(30)
                return self.check_latest_message(channel)
            return 0

    def check_slack_messages(self, channel: str) -> int:
        """Check Slack for messages."""
        if not config_options.getboolean("use_slack"):
            return
        # WebClient instantiates a client that can call API methods
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
            self.logger.info("Checking for new messages in %s", channel)
            # Call the conversations.history method using the WebClient
            # conversations.history returns the first 100 messages by default
            # These results are paginated, see:
            # https://api.slack.com/methods/conversations.history$pagination
            result = client.conversations_history(
                channel=channel_id,
                limit=1,
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
                    )

                    if response == 0:
                        return 0
                    else:
                        # print(f"responded to {msg_id}")
                        return 1
                else:
                    continue

            return 1

        except SlackApiError as error:
            error_msg = f"Error creating conversation: {format(error)}"
            self.logger.error(error_msg)

            if "rate_limited" in error_msg:
                time.sleep(30)
                return self.check_slack_messages(channel)

            return 0

    def find_id(self, msg_id):
        """Find the message ID in the slack ticket tracker csv file."""
        ticket = select_slack_ticket(msg_id)
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
            self._help_menu(channel_id=channel_id)
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
                status = _select_experiment_status(experiment_number)
                message = f"The status of experiment {experiment_number} is {status}."
                self.send_message(channel_id, message)
            except ValueError:
                message = "Please enter a valid experiment number."
                self.send_message(channel_id, message)
            return 1

        elif text[0:17] == "images experiment":
            # Get experiment number
            try:
                experiment_number = int(text[17:].strip())
                self._share_experiment_images(experiment_number)

            except ValueError:
                message = "Please enter a valid experiment number."
                self.send_message(channel_id, message)
            return 1
        elif text[0:11] == "vial status":
            self._vial_status(channel_id=channel_id)
            return 1

        elif text[0:11] == "well status":
            # Get well status
            self._well_status(channel_id=channel_id)
            return 1

        elif text[0:12] == "queue length":
            self._queue_length(channel_id=channel_id)
            return 1
        elif text[0:13] == "system status":
            self._queue_length(channel_id=channel_id)
            self._well_status(channel_id=channel_id)
            time.sleep(1)
            self._vial_status(channel_id=channel_id)
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
                self.send_message(channel_id, message)
            return 1

        elif text[0:7] == "status":
            system_status = system.select_system_status()
            message = f"The system status is {system_status}."
        elif text[0:5] == "pause":
            system.set_system_status(
                system.SystemState.PAUSE, "pausing ePANDA", self.testing
            )
            return 1

        elif text[0:6] == "resume":
            system.set_system_status(
                system.SystemState.RESUME, "resuming ePANDA", self.testing
            )
            return 1

        elif text[0:5] == "start":
            # system_state.set_system_status(system_state.SystemState.ON, "starting ePANDA", self.test)
            # start the experiment loop
            # controller.main()
            self.send_message(
                channel_id, "Sorry starting the ePANDA is not something I can do yet"
            )
            return 1

        elif text[0:4] == "shutdown":
            system.set_system_status(
                system.SystemState.SHUTDOWN, "stopping ePANDA", self.testing
            )
            return 1

        elif text[0:4] == "stop":
            system.set_system_status(
                system.SystemState.STOP, "stopping ePANDA", self.testing
            )
            self.send_message(channel_id, "Stopping the controller loop")
            return 1

        elif text[0:4] == "exit":
            # Exits the slackbot
            return 0

        else:
            message = "Sorry, I don't understand that command. Type !epanda help for commands I understand."
            self.send_message(channel_id, message)
            return 1

    def _help_menu(self, channel_id):
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
                "stop -> stops the experiment loop\n"
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
                "stop -> stops the experiment loop\n"
                "exit -> closes the slackbot\n"
            )
        self.send_message(channel_id, message)
        return 1

    def echem_error_procedure(self):
        """Procedure to follow when an echem error occurs."""

        channel_id = self.channel_id("alert")
        self.send_message(channel_id, "Failure has occurred. Please check the system.")
        self.take_screenshot(channel_id, "webcam")
        self.take_screenshot(channel_id, "vials")
        time.sleep(5)
        self.send_message(channel_id, "Would you like to continue? (y/n): ")
        while True:
            continue_decision = self.check_latest_message(channel_id)[0].strip().lower()
            if continue_decision == "y":
                return 1
            if continue_decision == "n":
                return 0
            time.sleep(5)

    def _vial_status(self, channel_id):
        """Sends the vial status to the user."""
        stock_msg, waste_msg = vial_status()
        self.send_message(channel_id, stock_msg)
        self.send_message(channel_id, waste_msg)
        return 1

    def _well_status(self, channel_id):
        """Sends the well status to the user."""
        table_msg = well_status()
        self.send_message(channel_id, table_msg)
        return 1

    def _queue_length(self, channel_id):
        # Get queue length
        message = f"The queue length is {count_queue_length()}."
        self.send_message(channel_id, message)
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
        self.send_message(channel_id, "Screenshots not implemented yet")

    def _share_experiment_images(self, experiment_id: int):
        """Share the images for an experiment."""
        # Look up there experiment_id in the db and find all results of type image
        # Then filter the results to only include those with dz in the name
        # Then send the images to slack

        results = select_specific_result(experiment_id, "image")
        if results == [] or results is None:
            message = f"Experiment {experiment_id} does not have any images. Or the experiment {experiment_id} does not exist."
            self.send_message("data", message)
            return
        for result in results:
            result: ExperimentResultsRecord
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
        # self._terminate_event = threading.Event()
        self.send_message("alert", "PANDA Bot is monitoring Slack")
        while self.status == 1:  # and not self._terminate_event.is_set():
            try:
                time.sleep(5)
                self.status = self.check_slack_messages(channel="alert")
                self.check_slack_messages(channel="data")
            except KeyboardInterrupt:
                break
            except Exception:
                # print(e)
                time.sleep(15)
                continue
        self.send_message("alert", "PANDA Bot is off duty")

    def off_duty(self):
        self.status = 0
        self.send_message("alert", "PANDA Bot is off duty")
        return

    # def terminate(self):
    #     """Terminate the slack bot."""
    #     self._terminate_event.set()


def vial_status(vial_type: Union[str, None] = None) -> tuple[str, str]:
    """
    Create formatted messages of the vial status and return them.
    Returns tuple of (stock_message, waste_message)
    """

    def get_stock_status_emoji(percentage: float) -> str:
        if percentage == 0 or math.isnan(percentage):
            return "⚫"
        elif percentage < 25:
            return "🔴"
        elif percentage < 50:
            return "🟡"
        else:
            return "🟢"

    def get_waste_status_emoji(percentage: float) -> str:
        if math.isnan(percentage):
            return "⚫"
        elif percentage < 50:
            return "🟢"
        elif percentage > 50:
            return "🟡"
        elif percentage > 75:
            return "🔴"

    # Get stock vials
    stock_vials = vials.read_vials("stock")[0]

    # Get waste vials
    waste_vials = vials.read_vials("waste")[0]

    # Format stock vials message
    stock_msg = "Stock Vials Status:\n```"
    for vial in stock_vials:
        percentage = (vial.volume / vial.capacity) * 100 if vial.capacity != 0 else 0
        emoji = get_stock_status_emoji(percentage)
        stock_msg += (
            f"\nPosition {vial.position}: {vial.contents} - {percentage:.1f}% {emoji}"
        )
    stock_msg += "\n```"

    # Format waste vials message
    waste_msg = "Waste Vials Status:\n```"
    for vial in waste_vials:
        percentage = (vial.volume / vial.capacity) * 100 if vial.capacity != 0 else 0
        emoji = get_waste_status_emoji(percentage)
        waste_msg += (
            f"\nPosition {vial.position}: {vial.name} - {percentage:.1f}% {emoji}"
        )
    waste_msg += "\n```"

    if vial_type == "stock":
        return stock_msg
    elif vial_type == "waste":
        return waste_msg
    else:
        return stock_msg, waste_msg


def well_status() -> str:
    """
    Create a plot of the well status and return the file path.
    """
    # Check current wellplate type
    plate_id, type_number, _ = select_current_wellplate_info()
    plate_type = select_well_characteristics(type_number)
    # Choose the correct wellplate object based on the wellplate type
    rows = plate_type.rows
    columns = plate_type.cols

    result = select_wellplate_wells()
    current_wells: List[Well] = []
    for row in result:
        try:
            if isinstance(row[5], str):
                incoming_contents = json.loads(row[5])
            else:
                incoming_contents = row[5]
        except json.JSONDecodeError:
            incoming_contents = {}
        except TypeError:
            incoming_contents = {}

        try:
            if isinstance(row[9], str):
                incoming_coordinates = json.loads(row[9])
            else:
                incoming_coordinates = row[9]
        except json.JSONDecodeError:
            incoming_coordinates = (0, 0)

        well_type_number = int(row[1]) if row[1] else 0
        volume = int(row[8]) if row[8] else 0
        capacity = int(row[10]) if row[10] else 0
        height = int(row[11]) if row[11] else 0
        experiment_id = int(row[6]) if row[6] else None
        project_id = int(row[7]) if row[7] else None

        current_wells.append(
            Well(
                well_id=str(row[2]),
                well_type_number=well_type_number,
                status=str(row[3]),
                status_date=str(row[4]),
                contents=incoming_contents,
                experiment_id=experiment_id,
                project_id=project_id,
                volume=volume,
                coordinates=incoming_coordinates,
                capacity=capacity,
                height=height,
                plate_id=int(plate_id),
            )
        )

    wells_and_status = {}
    for well in current_wells:
        status = well.status
        wells_and_status[well.well_id] = getattr(
            IconEmojies, status, IconEmojies.yellow
        )

    table = ""
    for row in rows:
        table += f"{row:>3} "
        for j in range(1, columns + 1):
            table += f"{wells_and_status[row + str(j)]:>3} "
        table += "\n"

    table = f"```\n{table}\n```"

    return table


def get_well_color(status: str) -> str:
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


class MockSlackBot(SlackBot):
    def __init__(self, test: bool = True):
        super().__init__(test=test)
        pass

    def send_message(self, channel_id: str, message) -> None:
        """Send a message to Slack."""
        # print(message)
        pass

    def send_slack_file(self, channel: str, file, message=None) -> int:
        """Send a file to Slack."""
        # print(f"File: {file}")
        pass

    def upload_images(self, channel, images, message):
        """Upload images to Slack."""
        # print(f"Images: {images}")
        pass

    def check_latest_message(self, channel: str) -> str:
        """Check Slack for the latest message."""
        # print("Checking latest message")
        pass

    def check_slack_messages(self, channel: str) -> int:
        """Check Slack for messages."""
        # print("Checking slack messages")
        pass

    def parse_slack_message(self, text: str, channel_id) -> int:
        """
        Parse the Slack message for commands.
        If command is valid, execute command and returns 0 else return 1.

        Valid commands: help, plot experiment #, share experiment #, status experiment #, vial status, well status, pause, resume, start, stop

        Args:
            message (str): The message to parse without the bot keyword !epanda.

        Returns:
            1 if command is valid, 0 if command is invalid
        """
        # print(f"Message: {text}")
        pass

    def echem_error_procedure(self):
        """Procedure to follow when an echem error occurs."""
        # print("Echem error procedure")
        pass

    def _vial_status(self, channel_id):
        """Sends the vial status to the user."""
        # print("Vial status")
        pass

    def _well_status(self, channel_id):
        """Sends the well status to the user."""
        # print("Well status")
        pass

    def _queue_length(self, channel_id):
        # print("Queue length")
        pass

    def take_screenshot(self, channel_id, camera_name: str):
        """Take a screenshot of the camera."""
        # print(f"Screenshot of {camera_name}")
        pass

    def _share_experiment_images(self, experiment_id: int):
        """Share the images for an experiment."""
        # print(f"Sharing images for experiment {experiment_id}")
        pass

    def channel_id(self, channel: str) -> str:
        """Return the channel ID based on the channel name."""
        return "channel_id"
        pass

    def run(self):
        """Run the slack bot."""
        # print("Running slack bot")
        pass

    def off_duty(self):
        # print("Off duty")
        pass

    def terminate(self):
        """Terminate the slack bot."""
        # print("Terminating slack bot")
        pass


def share_to_slack(
    experiment: ExperimentBase,
    logger: Logger = logging.getLogger("panda"),
    slack_bot: SlackBot = SlackBot(),
):
    """Share the results of the experiment to the slack data channel"""
    TESTING = read_testing_config()
    slack_bot = SlackBot()

    if experiment.results is None:
        logger.error("The experiment has no results")
        return
    if experiment.results.images is None:
        logger.error("The experiment has no image files")
        return
    try:
        exp_id = experiment.experiment_id

        if TESTING:
            msg = f"Experiment {exp_id} has completed with status {experiment.status}. Testing mode, no images to share"
            slack_bot.send_message("data", msg)
            return

        results = select_specific_result(exp_id, "images")

        if results is None:
            logger.error("The experiment %d has no image files", exp_id)
            msg = f"Experiment {exp_id} has completed with status {experiment.status} but has no image files to share"
            slack_bot.send_message("data", msg)
            return

        for result in results:
            result: ExperimentResultsRecord
            if "dz" not in result.result_value:
                results.remove(result)

        if len(results) == 0:
            logger.error("The experiment %d has no dz.tiff image files", exp_id)
            msg = f"Experiment {exp_id} has completed with status {experiment.status} but has no datazoned image files to share"
            slack_bot.send_message("data", msg)
            return

        msg = f"Experiment {exp_id} has completed with status {experiment.status}. Photos taken:"
        image_paths = [result.result_value for result in results]
        slack_bot.upload_images("data", image_paths, f"{msg}")
    except SlackApiError as error:
        logger.warning(
            "A Slack specific error occurred while sharing images from experiment %d with slack: %s",
            experiment.experiment_id,
            error,
        )
        # continue with the rest of the program

    except Exception as error:
        logger.warning(
            "An unanticipated error occurred while sharing images from experiment %d with slack: %s",
            experiment.experiment_id,
            error,
        )
        # continue with the rest of the program


if __name__ == "__main__":
    slack_bot = SlackBot(test=False)
    TEST_MESSAGE = "This is a test message."
    EPANDA_HELLO = """Hello ePANDA team! I am ePANDA..."""
    # slack_bot.check_slack_messages("alert")
    slack_bot.send_message("alert", TEST_MESSAGE)
