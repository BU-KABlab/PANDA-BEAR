"""Script to starting the ePANDA Slack Bot"""

from panda_lib.slack_tools.SlackBot import SlackBot
import argparse


def run_slack_bot(testing=False):
    """Run the SlackBot"""
    bot = SlackBot(test=testing)
    bot.run()


def main():
    parser = argparse.ArgumentParser(description="Run the Slack bot.")
    parser.add_argument(
        "--testing", action="store_true", help="Run the bot in testing mode."
    )
    parser.add_argument(
        "--production", action="store_true", help="Run the bot in production mode."
    )

    args = parser.parse_args()

    if args.testing:
        run_slack_bot(testing=True)
    elif args.production:
        run_slack_bot(testing=False)
    else:
        run_slack_bot(testing=True)


if __name__ == "__main__":
    main()
