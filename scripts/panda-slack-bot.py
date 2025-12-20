#!/usr/bin/env python3
"""
Standalone Slack Bot Runner for PANDA SDL

This script runs the PANDA Slack bot as a standalone process, allowing it to
operate in parallel with the main PANDA SDL application.

Usage:
    python scripts/panda-slack-bot.py [--testing] [--production]

Or use the provided shell scripts:
    scripts/run_slack_bot.sh        # Linux/Mac
    scripts/run_slack_bot_windows.bat  # Windows
"""

import argparse
import sys
from pathlib import Path

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from panda_lib.slack_tools.slackbot_module import SlackBot


def main():
    """Main entry point for standalone Slack bot."""
    parser = argparse.ArgumentParser(
        description="Run the PANDA Slack bot as a standalone process.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in production mode (default)
  python scripts/panda-slack-bot.py

  # Run in testing mode
  python scripts/panda-slack-bot.py --testing

  # Explicitly set production mode
  python scripts/panda-slack-bot.py --production

Note: The bot will monitor Slack channels for commands and can be used
to control and monitor the PANDA SDL system remotely.
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
