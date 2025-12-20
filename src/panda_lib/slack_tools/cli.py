"""
Command-line interface for running the PANDA Slack bot as a standalone process.

This module provides a CLI entry point that can be used via the `panda-slack-bot`
command after installation, or directly via Python.
"""

import argparse
import sys

from .slackbot_module import SlackBot


def main():
    """Main entry point for the panda-slack-bot CLI command."""
    parser = argparse.ArgumentParser(
        description="Run the PANDA Slack bot as a standalone process.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in production mode (default)
  panda-slack-bot

  # Run in testing mode
  panda-slack-bot --testing

  # Explicitly set production mode
  panda-slack-bot --production

Note: The bot will monitor Slack channels for commands and can be used
to control and monitor the PANDA SDL system remotely. This can run in
parallel with the main PANDA SDL application.
        """,
    )

    parser.add_argument(
        "--testing",
        action="store_true",
        help="Run the bot in testing mode (no real Slack API calls)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run the bot in production mode (explicit, default behavior)",
    )

    args = parser.parse_args()

    # Determine mode (testing takes precedence if both specified)
    testing_mode = args.testing and not args.production

    try:
        # Initialize and run the bot
        bot = SlackBot(test=testing_mode)
        bot.send_message("alert", "PANDA Bot is monitoring Slack (standalone mode)")

        # Run the bot's main loop
        bot.run()

    except KeyboardInterrupt:
        print("\nShutting down Slack bot...")
        bot.off_duty()
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if "bot" in locals():
            bot.off_duty()
        sys.exit(1)


if __name__ == "__main__":
    main()
