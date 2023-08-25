"""sendSlackMessages.py"""
# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
import csv
from datetime import datetime
import json
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import slack_credentials as slack_cred
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="slack_bot.log",
    filemode="a",
    format="%(asctime)s - %(name)% - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def send_slack_message(channel_id: str, message) -> None:
    """
    Sends a message to a Slack channel using the Slack API.

    Args:
    message (str): The message to send.

    Returns:
    None
    """
    # WebClient insantiates a client that can call API methods
    # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
    client = WebClient(slack_cred.TOKEN)
    # ID of the channel you want to send the message to
    if channel_id == "conversation":
        channel_id = slack_cred.CONVERSATION_CHANNEL_ID  # epanda-alerts channel
    elif channel_id == "alert":
        channel_id = slack_cred.ALERT_CHANNEL_ID  # epanda-alerts channel

    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(channel=channel_id, text=message)
        # print(result)
        logging.info("Message sent: %s", message)

    except SlackApiError as error:
        logging.error("Error posting message: %s", error)


def send_slack_file(channel: str, file, message=None) -> None:
    """Send a file to a Slack channel using the Slack API."""
    # Get image file name without the path
    filename_to_post = file.split("\\")[-1]

    # WebClient insantiates a client that can call API methods
    # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
    client = WebClient(slack_cred.TOKEN)
    # The name of the file you're going to upload
    # ID of channel that you want to upload file to
    if channel == "conversation":
        channel_id = slack_cred.CONVERSATION_CHANNEL_ID
    elif channel == "alert":
        channel_id = slack_cred.ALERT_CHANNEL_ID
    else:
        return "No applicable channel"

    try:
        # Call the files.upload method using the WebClient
        # Uploading files requires the `files:write` scope
        result = client.files_upload_v2(
            channel=channel_id,
            file=filename_to_post,
            filename=file,
            initial_comment=message,
        )
        # Log the result
        # print(result)
        logging.info("File sent: %s", file)

    except SlackApiError as exception:
        log_msg = f"Error uploading file: {format(exception)}"
        logging.error(log_msg)

    def upload_requested_experiment_info(experimentID, test_type, result_type, channel):
        """Uploads requested experiment information to Slack channel.

        Args:
            experimentID (int): The ID of the experiment to get information from.
            test_type (str): CV, CA, or OCP
            result_type (str): plot/graph, data, .
            channel (str): The Slack channel to upload the information to.

        """
        # clean inputs
        experimentID = int(experimentID)
        test_type = test_type.lower()
        result_type = result_type.lower()
        channel = channel.lower()

        # Get experiment information
        match result_type:
            case "plot":
                # Get plot
                pass
            case "graph":
                # Get plot
                pass

            case "data":
                # Get data
                pass
            case "parameters":
                # Get parameters
                pass
            case _:
                return "No applicable result type"


def check_slack_messages(channel: str):
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
        return "No applicable channel"

    # latestTS = datetime.now().timestamp()

    try:
        logging.info("Checking for new messages.")
        # Call the conversations.history method using the WebClient
        # conversations.history returns the first 100 messages by default
        # These results are paginated, see: https://api.slack.com/methods/conversations.history$pagination
        result = client.conversations_history(channel=channel_id)

        conversation_history = result["messages"]

        # Eliminate messages with not text value, as this throws error with scipy.io.savemat function
        conversation_history2 = [
            x
            for x in conversation_history
            if (x["text"][0:7] == "!epanda")
            or (x["text"][0:7] == "!EPANDA")
            or (x["text"][0:7] == "!ePANDA")
            or (x["text"][0:7] == "!Epanda")
            or (x["text"][0:7] == "!ePanda")
        ]

        for message, payload in enumerate(conversation_history2):
            msg_id = payload["client_msg_id"]
            msg_text = payload["text"]
            msg_ts = payload["ts"]
            lookup_tickets = find_id(msg_id)
            if lookup_tickets is False:
                # Send message to Slack
                logging.info("New message found: %s", msg_text)
                response = parse_slack_message(msg_text[8:].rstrip(), channel_id)
                # Add message to csv file
                with open(
                    Path(__file__).parents[0] / "slack_ticket_tracker.csv",
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

        # Print results
        # print(json.dumps(conversation_history2, indent=2))

    except SlackApiError as error:
        error_msg = f"Error creating conversation: {format(error)}"
        logging.error(error_msg)


def find_id(id):
    """Find the message ID in the slack ticket tracker csv file."""
    with open(
        Path(__file__).parents[0] / "slack_ticket_tracker.csv",
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
            if row["msg_id"] == id:
                return row
    return False


def parse_slack_message(text: str, channel_id) -> int:
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
        message = (
            "Here is a list of commands I understand:\n"
            "help - displays this message\n"
            "plot experiment # - plots plots the CV data for experiment #\n"
            "data experiment # - sends the data files for experiment #\n"
            "status experiment # - displays the status of experiment #\n"
            "status vials - displays the status of the vials\n"
            "status wells - displays the status of the wells\n"
            "pause - pauses the current experiment\n"
            "resume - resumes the current experiment\n"
            "start - starts a new experiment\n"
            "stop - stops the current experiment\n"
        )
        send_slack_message(channel_id, message)

    elif text[0:15] == "plot experiment":
        # Get experiment number
        experiment_number = text[5:]
        # Get plot
        pass

    elif text[0:15] == "data experiment":
        # Get experiment number
        experiment_number = text[6:]
        # Share experiment
        return 1

    elif text[0:17] == "status experiment":
        # Get experiment number
        experiment_number = text[7:]
        # Get status
        return 1

    elif text[0:11] == "vial status":
        # Get vial status
        return 1

    elif text[0:11] == "well status":
        # Get well status
        return 1

    elif text[0:5] == "pause":
        return 1

    elif text[0:6] == "resume":
        return 1

    elif text[0:5] == "start":
        return 1

    elif text[0:4] == "stop":
        return 1

    else:
        message = "Sorry, I don't understand that command. Type !epanda help for a list of commands."
        send_slack_message(channel_id, message)
        return 0


if __name__ == "__main__":
    TEST_MESSAGE = "This is a test message."
    ePANDA_hello = "Hello ePANDA team! I am ePANDA. I am here to help you with your experiments. I can run experiments, analyze data, and send you alerts. I am still learning, so please be patient with me. I am excited to work with you!"
    # send_slack_message('alert', MESSAGE)
    # send_slack_file('alert', r'code\misc_code_testing\ePANDA_pro_pic.jpeg', ePANDA_hello)
    check_slack_messages("alert")
