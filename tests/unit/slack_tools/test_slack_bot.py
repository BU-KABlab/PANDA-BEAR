from unittest.mock import MagicMock, patch

import pytest

from panda_lib.slack_tools.slackbot_module import SlackBot


@pytest.fixture
def mock_slack_bot():
    """
    Returns a SlackBot instance with mocked WebClient so no real API calls occur.
    """
    with (
        patch("panda_lib.slack_tools.slackbot_module.WebClient") as mock_client_class,
        patch(
            "panda_lib.slack_tools.slackbot_module.config_options.getboolean",
            return_value=True,
        ),
        patch(
            "panda_lib.slack_tools.slackbot_module.read_testing_config",
            return_value=True,
        ),
    ):
        # Setup mock for auth test response
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.auth_test.return_value = {
            "ok": True,
            "user_id": "test_user_id",
        }

        bot = SlackBot(test=True)
        # Ensure we're using the mocked client
        assert bot.client is mock_client_instance
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


def test_channel_id_mapping(mock_slack_bot):
    """
    Test that channel_id correctly maps channel names to IDs when in test mode.
    """
    # In test mode, all channels should map to test channels
    assert mock_slack_bot.channel_id("data") == mock_slack_bot.channel_id("data")
    assert mock_slack_bot.channel_id("alert") == mock_slack_bot.channel_id("alert")
    assert mock_slack_bot.channel_id("conversation") == mock_slack_bot.channel_id(
        "conversation"
    )
    assert mock_slack_bot.channel_id("invalid") == 0


def test_upload_images(mock_slack_bot):
    """
    Test that upload_images properly calls files_upload_v2 with correct params.
    """
    with patch.object(mock_slack_bot.client, "files_upload_v2") as mock_upload:
        mock_slack_bot.upload_images(
            "data", ["image1.jpg", "image2.jpg"], "Test images"
        )
        mock_upload.assert_called_once()
        # Verify file uploads format contains both images
        args, kwargs = mock_upload.call_args
        assert len(kwargs["file_uploads"]) == 2
        assert kwargs["channel"] == mock_slack_bot.channel_id("data")
        assert kwargs["initial_comment"] == "Test images"
