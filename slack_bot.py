"""Script to starting and stopping the ePANDA Slack Bot"""

import time
from panda_lib.slack_tools.SlackBot import SlackBot

#pylint: disable=broad-exception-caught
choose_testing_mode = input("Testing? (y/n): ").strip().lower()
TEST = False
if choose_testing_mode[0] == "y":
    TEST = True

bot = SlackBot(test=TEST)
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
