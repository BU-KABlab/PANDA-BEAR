"""Script to starting the ePANDA Slack Bot"""

import argparse
import time

from panda_lib.slack_tools.SlackBot import SlackBot


def run_slack_bot(testing=False):
    """Runs the slack monitor bot."""
    while True:
        try:
            bot = SlackBot(test=testing)
            bot.send_message("alert", "PANDA Bot is monitoring Slack")
            try:
                time.sleep(15)
                bot.check_slack_messages(channel="alert")
                time.sleep(1)
                bot.check_slack_messages(channel="data")
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(60)
                continue
        except Exception as e:
            print(f"An error occurred: {e}")
            return

        finally:
            bot.off_duty()


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
