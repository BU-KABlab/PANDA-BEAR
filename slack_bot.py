"""Script to starting and stopping the ePANDA Slack Bot"""

import time
from epanda_lib.slack_tools.SlackBot import SlackBot

bot = SlackBot(test=False)
print("Starting Slack Bot")
STATUS = bot.check_slack_messages(channel="alert")
while STATUS == 1:
    try:
        time.sleep(5)
        STATUS = bot.check_slack_messages(channel="alert")
        bot.check_slack_messages(channel="data")
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(e)
        time.sleep(15)
        continue

print("Stopping Slack Bot")
