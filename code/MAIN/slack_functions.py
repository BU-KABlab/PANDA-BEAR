'''sendSlackMessages.py'''
# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
import logging
import slack_credentials as slack_cred
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def send_slack_message(message):
    """
    Sends a message to a Slack channel using the Slack API.

    Args:
    message (str): The message to send.

    Returns:
    None
    """
    # WebClient insantiates a client that can call API methods
    # When using Bolt, you can use either `app.client` or the `client` passed to listeners.
    client = WebClient(slack_cred.o_auth_token)
    # ID of the channel you want to send the message to
    #channel_id = slack_cred.epabda_conversation #epanda-alerts channel
    channel_id = slack_cred.epabda_alerts_channel_id #epanda-alerts channel

    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        print(result)

    except SlackApiError as error:
        logging.error("Error posting message: %s", error)

if __name__ == "__main__":
    MESSAGE = "This is a test message."
    send_slack_message(MESSAGE)
