# Slack Bot Organization

## Overview

The PANDA Slack bot can be used in two ways:
1. **Integrated mode**: Automatically runs as part of the PANDA SDL experiment loop
2. **Standalone mode**: Runs as a separate process in parallel with PANDA SDL

## Architecture

### Core Module
- **Location**: `src/panda_lib/slack_tools/slackbot_module.py`
- **Purpose**: Contains the `SlackBot` class used by both integrated and standalone modes
- **Usage**: Imported by `experiment_loop.py` for integrated operation

### Standalone Entry Points

#### Option 1: CLI Command (Recommended)
After installing the package, use:
```bash
panda-slack-bot [--testing] [--production]
```

#### Option 2: Python Script
```bash
python scripts/panda-slack-bot.py [--testing] [--production]
```

#### Option 3: Shell Scripts
- **Linux/Mac**: `src/panda_lib/slack_tools/run_slack_bot.sh`
- **Windows**: `src/panda_lib/slack_tools/run_slack_bot_windows.bat`

## Usage Scenarios

### Running Standalone (Parallel to PANDA SDL)

The Slack bot can run independently to monitor and control PANDA SDL:

```bash
# Terminal 1: Run PANDA SDL
panda-cli

# Terminal 2: Run Slack bot in parallel
panda-slack-bot
```

### Running in Testing Mode

For development or when Slack is not configured:

```bash
panda-slack-bot --testing
```

This mode:
- Doesn't make real Slack API calls
- Uses mock responses
- Useful for testing and development

## Configuration

The bot reads configuration from:
- Environment variable: `PANDA_SDL_CONFIG_PATH` (points to config file)
- Config file section: `[SLACK]`
- Config file section: `[OPTIONS]` (for `use_slack` flag)

Required config values:
```ini
[SLACK]
slack_token = your_slack_token
slack_alert_channel_id = C1234567890
slack_data_channel_id = C0987654321
slack_conversation_channel_id = C1122334455

[OPTIONS]
use_slack = True
```

## Integration with PANDA SDL

### In Experiment Loop
The experiment loop creates its own `SlackBot` instance:
```python
from panda_lib.slack_tools.slackbot_module import SlackBot

controller_slack = SlackBot(test=use_mock_instruments)
controller_slack.send_message("alert", "PANDA_SDL is starting up")
```

### Standalone Operation
The standalone bot runs its own monitoring loop:
```python
bot = SlackBot(test=testing_mode)
bot.run()  # Runs continuous monitoring loop
```

## Benefits of This Organization

1. **No Duplication**: Single `SlackBot` class used everywhere
2. **Flexibility**: Can run integrated or standalone
3. **Maintainability**: Changes to `SlackBot` affect both modes
4. **Professional Structure**: Follows Python packaging best practices
5. **Easy Deployment**: CLI command makes it easy to run as a service

## Migration from Old `slack_bot.py`

The old root-level `slack_bot.py` has been replaced with:
- **CLI command**: `panda-slack-bot` (after `pip install`)
- **Script**: `scripts/panda-slack-bot.py` (direct execution)
- **Shell scripts**: Updated to use new entry points

All functionality is preserved, just better organized.

## Troubleshooting

### Bot Not Responding
1. Check Slack token is valid in config
2. Verify `use_slack = True` in config
3. Check bot has permissions in Slack channels
4. Review logs for errors

### Running Both Integrated and Standalone
You can run both, but be aware:
- Both will respond to Slack commands
- May cause duplicate responses
- Consider using different channels or disabling one mode

### Testing Mode
When `--testing` is used:
- No real Slack API calls
- All methods return mock responses
- Useful for development without Slack setup
