'''sendSlackMessages.py'''
# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
import logging
import slack_credentials as slack_cred
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def send_slack_message(channel: str, message):
    """
    Sends a message to a Slack channel using the Slack API.

    Args:
    message (str): The message to send.

    Returns:
    None
    """
    # WebClient insantiates a client that can call API methods
    # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
    client = WebClient(slack_cred.token)
    # ID of the channel you want to send the message to
    if channel == 'conversation':
        channel_id = slack_cred.conversation_channel_id #epanda-alerts channel
    elif channel == 'alert':
        channel_id = slack_cred.alert_channel_id #epanda-alerts channel
    else:
        return 'No applicable channel'

    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        print(result)

    except SlackApiError as error:
        logging.error("Error posting message: %s", error)


def send_slack_file(channel: str, file, message = None):
    '''Send a file to a Slack channel using the Slack API.'''
    # Get image file name
    filename_to_post = file

    # WebClient insantiates a client that can call API methods
    # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
    client = WebClient(slack_cred.token)
    # The name of the file you're going to upload
    file_name = "./TestImage.gif"
    # ID of channel that you want to upload file to
    if channel == 'conversation':
        channel_id = slack_cred.conversation_channel_id
    elif channel == 'alert':
        channel_id = slack_cred.alert_channel_id
    else:
        return 'No applicable channel'

    try:
        # Call the files.upload method using the WebClient
        # Uploading files requires the `files:write` scope
        result = client.files_upload(
            channels=channel_id,
            file=filename_to_post,
            filename=file_name,
            filetype="gif",
            initial_comment=message
        )
        # Log the result
        print(result)

    except SlackApiError as e:
        print("Error uploading file: {}".format(e))
if __name__ == "__main__":
    MESSAGE = "This is a test message."
    send_slack_message('alert', MESSAGE)
