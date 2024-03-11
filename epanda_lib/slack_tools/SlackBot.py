"""sendSlackMessages.py"""

# pylint: disable=line-too-long

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from epanda_lib.config.config import (QUEUE, SLACK_TICKETS, STOCK_STATUS, WASTE_STATUS,
                            WELL_STATUS, WELL_TYPE)
from epanda_lib.config.secrets import Slack as slack_cred
from epanda_lib.wellplate import CircularWellPlate, GraceBioLabsWellPlate, Wellplate


class SlackBot:
    """Class for sending messages to Slack."""

    def __init__(self, test: bool = False):
        # Set up logging
        # logger = logging.getLogger(__name__)
        # logger.setLevel(logging.DEBUG)
        # formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
        # file_handler = logging.FileHandler("code/logs/slack_bot.log")
        # system_handler = logging.FileHandler("code/logs/ePANDA.log")
        # file_handler.setFormatter(formatter)
        # system_handler.setFormatter(formatter)
        # logger.addHandler(file_handler)
        # logger.addHandler(system_handler)
        self.logger = logging.getLogger("e_panda")
        self.test = test

    def send_slack_message(self, channel_id: str, message) -> None:
        """Send a message to Slack."""
        client = WebClient(slack_cred.TOKEN)
        if channel_id == "conversation":
            channel_id = slack_cred.CONVERSATION_CHANNEL_ID
        elif channel_id == "alert":
            channel_id = slack_cred.ALERT_CHANNEL_ID
        elif channel_id == "data":
            channel_id = slack_cred.DATA_CHANNEL_ID

        try:
            if not self.test:
                result = client.chat_postMessage(channel=channel_id, text=message)
            else:
                result = {"ok": True}
                print("Slack:", message)
            if result["ok"]:
                self.logger.info("Message sent:%s", message)
            else:
                self.logger.error("Error sending message:%s", message)
        except SlackApiError as error:
            self.logger.error("Error posting message: %s", error)

    def send_slack_file(self, channel: str, file, message=None) -> int:
        """Send a file to Slack."""
        client = WebClient(slack_cred.TOKEN)
        file = Path(file)
        filename_to_post = file.name

        if channel == "conversation":
            channel_id = slack_cred.CONVERSATION_CHANNEL_ID
        elif channel == "alert":
            channel_id = slack_cred.ALERT_CHANNEL_ID
        elif channel == "data":
            channel_id = slack_cred.DATA_CHANNEL_ID
        elif channel in [
            slack_cred.CONVERSATION_CHANNEL_ID,
            slack_cred.ALERT_CHANNEL_ID,
        ]:
            channel_id = channel
        else:
            return 0

        try:
            if not self.test:
                result = client.files_upload_v2(
                    channel=channel_id,
                    file=file.open("rb"),
                    filename=filename_to_post,
                    initial_comment=message,
                )
            else:
                result = {"ok": True}
            if result["ok"]:
                self.logger.info("File sent: %s", file)
                return 1
            else:
                self.logger.error("Error sending file: %s", file)
                return 0
        except SlackApiError as exception:
            log_msg = f"Error uploading file: {format(exception)}"
            self.logger.error(log_msg)
            return 0

    def check_slack_messages(self, channel: str) -> int:
        """Check Slack for messages."""

        # WebClient insantiates a client that can call API methods
        # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
        client = WebClient(token=slack_cred.TOKEN)
        # Store conversation history
        conversation_history = []
        # ID of the channel you want to send the message to
        if channel == "conversation":
            channel_id = slack_cred.CONVERSATION_CHANNEL_ID
        elif channel == "alert":
            channel_id = slack_cred.ALERT_CHANNEL_ID
        else:
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
                limit=5,
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
                msg_text = payload["text"]
                msg_ts = payload["ts"]
                lookup_tickets = self.find_id(msg_id)
                if lookup_tickets is False:
                    # Send message to Slack
                    logging.info("New message found: %s", msg_text)
                    response = self.parse_slack_message(
                        msg_text[8:].rstrip(), channel_id
                    )
                    # Add message to csv file
                    with open(
                        SLACK_TICKETS,
                        "a",
                        newline="",
                        encoding="utf-8",
                    ) as csvfile:
                        writer = csv.DictWriter(
                            csvfile,
                            fieldnames=[
                                "msg_id",
                                "channel_id",
                                "msg_txt",
                                "valid_cmd",
                                "ts",
                                "addressed_ts",
                            ],
                        )
                        writer.writerow(
                            {
                                "msg_id": msg_id,
                                "channel_id": channel_id,
                                "msg_txt": msg_text,
                                "valid_cmd": response,
                                "ts": msg_ts,
                                "addressed_ts": datetime.now().timestamp(),
                            }
                        )
                    if response == 0:
                        return 0
                    else:
                        print(f"responded to {msg_id}")
                        return 1
                else:
                    continue

            return 1
            # Print results
            # print(json.dumps(conversation_history2, indent=2))

        except SlackApiError as error:
            error_msg = f"Error creating conversation: {format(error)}"
            self.logger.error(error_msg)
            return 0

    def find_id(self, experiment_id):
        """Find the message ID in the slack ticket tracker csv file."""
        with open(
            SLACK_TICKETS,
            newline="",
            encoding="utf-8",
        ) as csvfile:
            reader = csv.DictReader(
                csvfile,
                fieldnames=[
                    "msg_id",
                    "channel_id",
                    "msg_txt",
                    "valid_cmd",
                    "ts",
                    "addressed_ts",
                ],
            )
            for row in reader:
                if row["msg_id"] == experiment_id:
                    return row
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

        elif text[0:17] == "status experiment":
            # Get experiment number
            # experiment_number = text[7:]
            # Get status
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
        elif text[0:6] == "status":
            self.__queue_length(channel_id=channel_id)
            self.__well_status(channel_id=channel_id)
            time.sleep(1)
            self.__vial_status(channel_id=channel_id)
            return 1
        elif text[0:5] == "pause":
            return 1

        elif text[0:6] == "resume":
            return 1

        elif text[0:5] == "start":
            return 1

        elif text[0:4] == "stop":
            return 1

        elif text[0:4] == "exit":
            return 0

        else:
            message = "Sorry, I don't understand that command. Type !epanda help for commands I understand."
            self.send_slack_message(channel_id, message)
            return 1

    def __help_menu(self, channel_id):
        """Sends the help menu to the user."""
        message = (
            "Here is a list of commands I understand:\n"
            "help - displays this message\n"
            # "plot experiment # - plots plots the CV data for experiment #\n"
            # "data experiment # - sends the data files for experiment #\n"
            # "status experiment # - displays the status of experiment #\n"
            "vial status - displays the status of the vials\n"
            "well status - displays the status of the wells and the rest of the deck\n"
            "queue length - displays the length of the queue\n"
            "status - displays the status of the vials, wells, and queue\n"
            # "pause - pauses the experiment loop\n"
            # "resume - resumes the experiment loop\n"
            # "start - starts the experiment loop\n"
            # "stop - stops the experiment loop\n"
            "exit - closes the slackbot\n"
        )
        self.send_slack_message(channel_id, message)
        return 1

    def __vial_status(self, channel_id):
        """Sends the vial status to the user."""
        # Get vial status
        ## Load the vial status json file
        stock_vials = pd.read_json(STOCK_STATUS)
        ## Filter for just the vial position and volume
        stock_vials = stock_vials[["position", "volume", "name"]]
        # Drop any vials that have null values
        stock_vials = stock_vials.dropna()
        ## set position to be a string and volume to be a float
        stock_vials["position"] = stock_vials["position"].astype(str)
        stock_vials["volume"] = stock_vials["volume"].astype(float)
        ## Create a bar graph with volume on the x-axis and position on the y-axis
        ## Send the graph to slack
        plt.bar(
            stock_vials["position"],
            stock_vials["volume"],
            align="center",
            alpha=0.5,
            color="blue",
        )
        # label each bar with the volume
        for i, v in enumerate(stock_vials["volume"]):
            plt.text(i, v, str(round(v, 4)), color="black", ha="center")

        # Draw a horizontal line at 4000
        plt.axhline(y=2000, color="red", linestyle="-")
        # Write the name of the vial vertically in the bar
        for i, v in enumerate(stock_vials["name"]):
            plt.text(i, 10, str(v), color="black", ha="center", rotation=90)
        plt.xlabel("Position")
        plt.ylabel("Volume")
        plt.title("Stock Vial Status")
        plt.savefig("vial_status.png")
        self.send_slack_file(channel_id, "vial_status.png")

        ## Delete the graph file
        Path("vial_status.png").unlink()
        plt.close()

        # And the same for the waste vials
        waste_vials = pd.read_json(WASTE_STATUS)
        waste_vials = waste_vials[["position", "volume", "name"]]
        # Drop any vials that have null values
        waste_vials = waste_vials.dropna()
        waste_vials["position"] = waste_vials["position"].astype(str)
        waste_vials["volume"] = waste_vials["volume"].astype(float)
        plt.bar(
            waste_vials["position"],
            waste_vials["volume"],
            align="center",
            alpha=0.5,
            color="blue",
        )
        for i, v in enumerate(waste_vials["volume"]):
            plt.text(i, v, str(round(v, 4)), color="black", ha="center")
        plt.axhline(y=20000, color="red", linestyle="-")
        for i, v in enumerate(waste_vials["name"]):
            plt.text(i, 10, str(v), color="black", ha="center", rotation=90)
        plt.xlabel("Position")
        plt.ylabel("Volume")
        plt.title("Waste Vial Status")
        plt.savefig("waste_status.png")
        self.send_slack_file(channel_id, "waste_status.png")
        Path("waste_status.png").unlink()
        plt.close()

    def __well_status(self, channel_id):
        """Sends the well status to the user."""
        # Check current wellplate type
        with open(WELL_STATUS, "r", encoding="utf-8") as well:
            data = json.load(well)
            type_number = data["type_number"]
        with open(WELL_TYPE, "r", encoding="utf-8") as well:
            data = csv.reader(well)
            for row in data:
                if str(row[0]) == str(type_number):
                    wellplate_type = str(row[4]).strip()
                    break

        # Choose the correct wellplate object based on the wellplate type
        wellplate: Wellplate = None
        if wellplate_type == "circular":
            wellplate = CircularWellPlate(
                a1_x=-218,
                a1_y=-74,
                orientation=0,
                columns="ABCDEFGH",
                rows=13,
                type_number=type_number,
            )
        elif wellplate_type == "square":
            wellplate = GraceBioLabsWellPlate(
                a1_x=-218,
                a1_y=-74,
                orientation=0,
                columns="ABCDEFGH",
                rows=13,
                type_number=type_number,
            )

        ## Well coordinate
        x_coordinates, y_coordinates, color = (
            wellplate.well_coordinates_and_status_color()
        )
        if wellplate.shape == "circular":
            marker = "o"
        else:
            marker = "s"

        ## Label the wellplate with the plate id below the bottom row and centered to the wellplate
        # get the coordinates of wells H12 and A12
        h12: dict = wellplate.get_coordinates("H12")
        a12: dict = wellplate.get_coordinates("A12")
        # calculate the center of the wellplate
        center = h12["x"] + (a12["x"] - h12["x"]) / 2
        # plot the plate id
        plt.text(
            center, h12["y"] - 20, str(wellplate.plate_id), color="black", ha="center"
        )

        ## Vial coordinates
        vial_x = []
        vial_y = []
        vial_color = []
        vial_marker = []  # a circle for these circular vials
        ## Vials
        with open(WASTE_STATUS, "r", encoding="utf-8") as stock:
            data = json.load(stock)
            for vial in data:
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
        with open(STOCK_STATUS, "r", encoding="utf-8") as stock:
            data = json.load(stock)
            for vial in data:
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

        # rinse_vial = {"x": -411, "y": -30}
        # vial_x.append(rinse_vial["x"])
        # vial_y.append(rinse_vial["y"])
        # vial_color.append("black")
        ## combine the well and vial coordinates
        # x_coordinates.extend(stock_vial_x)
        # y_coordinates.extend(stock_vial_y)
        # color.extend(vial_color)

        # Plot the well plate
        plt.scatter(
            x_coordinates, y_coordinates, marker=marker, c=color, s=75, alpha=0.5
        )
        plt.scatter(vial_x, vial_y, marker="o", c=vial_color, s=200, alpha=1)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Status of Stage Items")
        plt.grid(True, "both")
        plt.xlim(-420, 10)
        plt.ylim(-310, 10)
        plt.savefig("well_status.png", format="png")
        plt.close()
        # Send the plot to Slack
        self.send_slack_file(channel_id, "well_status.png")
        Path("well_status.png").unlink()
        return 1

    def __queue_length(self, channel_id):
        # Get queue length
        queue_length = 0
        queue_file = pd.read_csv(
            QUEUE,
            skipinitialspace=True,
            header=None,
            names=["id", "priority", "filename", "protocol_type"],
        )
        # the columsn to id,priority,filename,protocol_type
        queue_length = len(queue_file) - 1
        message = f"The queue length is {queue_length}."
        self.send_slack_message(channel_id, message)
        return 1


if __name__ == "__main__":
    slack_bot = SlackBot(test=False)
    TEST_MESSAGE = "This is a test message."
    EPANDA_HELLO = """Hello ePANDA team! I am ePANDA..."""
    # slack_bot.check_slack_messages("alert")
    slack_bot.send_slack_message("alert", TEST_MESSAGE)
