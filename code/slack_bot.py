"""Script to starting and stopping the ePANDA Slack Bot"""
import time
from slack_functions2 import SlackBot

bot = SlackBot(test = False)
STATUS = bot.check_slack_messages(channel="alert")
while STATUS == 1:
    time.sleep(15)
    STATUS = bot.check_slack_messages(channel="alert")
