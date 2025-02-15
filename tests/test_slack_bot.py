from unittest.mock import MagicMock, patch

import pytest

from panda_lib.slack_tools.SlackBot import SlackBot


@pytest.fixture
def mock_slack_bot():
    """
    Returns a SlackBot instance with mocked WebClient so no real API calls occur.
    """
    with patch("panda_lib.slack_tools.SlackBot.WebClient") and patch(
        "panda_lib.slack_tools.SlackBot.config_options.getboolean", return_value=True
    ):
        bot = SlackBot(test=True)
        yield bot


def test_send_message(mock_slack_bot):
    """
    Verify that send_message calls chat_postMessage with correct data.
    """
    with patch.object(mock_slack_bot.client, "chat_postMessage") as mock_chat:
        mock_slack_bot.send_message("data", "Hello test")
        mock_chat.assert_called_once_with(
            channel=mock_slack_bot.channel_id("data"), text="Hello test"
        )


def test_send_slack_file(mock_slack_bot):
    """
    Ensure send_slack_file will open and upload a file without real Slack calls.
    """
    with (
        patch.object(mock_slack_bot.client, "files_upload_v2") as mock_upload,
        patch("builtins.open", MagicMock()),
    ):
        mock_slack_bot.send_slack_file("alert", "fake_path.jpg", message="Test file")
        mock_upload.assert_called_once()
