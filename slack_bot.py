"""Script to starting and stopping the ePANDA Slack Bot"""

from panda_lib.slack_tools.SlackBot import SlackBot

#pylint: disable=broad-exception-caught
choose_testing_mode = input("Testing? (y/n): ").strip().lower()
TEST = True if choose_testing_mode[0] == "y" else False

bot = SlackBot(test=TEST)
print("Starting Slack Bot")
bot.run()
