"""Script to starting and stopping the ePANDA Slack Bot"""

import threading
from panda_lib.slack_tools.SlackBot import SlackBot

TEST = True

def run_slack_bot():
    """Run the SlackBot"""
    bot = SlackBot(test=TEST)
    print("Starting Slack Bot")
    bot.run()

# Create a thread to run the SlackBot
slack_bot_thread = threading.Thread(target=run_slack_bot)

# Start the thread
slack_bot_thread.start()

# Optionally, you can join the thread if you want the main program to wait for it to finish
slack_bot_thread.join()
