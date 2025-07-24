# Getting Started with PANDA-SDL

This guide will help you set up your environment and get started with the PANDA-SDL system. Follow these steps to install the required software, configure your environment, and run your first experiment.

## Prerequisites

Before you begin, ensure you have the following:

- **Python 3.10** installed on your system
- A compatible operating system:
  - Windows (recommended due to Gamry potentiostat dependency)
  - Debian-based Linux (with limitations on potentiostat functionality)
- Administrator/sudo privileges for installing system dependencies

## Installation

### 1. Clone the Repository

First, clone the PANDA-SDL repository to your local machine:

```bash
git clone https://github.com/BU-KABlab/PANDA-SDL.git
cd PANDA-SDL
```

### 2. Drivers and SDKs

#### FLIR SDK

If your PANDA system uses FLIR cameras for imaging:

1. Download the SDK (version >= 4.2 ) from [FLIR's website](https://www.flir.com/products/spinnaker-sdk/)
2. Install the system SDK
3. Note the path to the corresponding Python wheel file (`.whl`)

Might look something like:

`C:\Users\<your name>\Downloads\spinnaker_python-4.2.#.###-cp310-cp310-win_amd64\spinnaker_python-4.2.#.###-cp310-cp310-win_amd64.whl`

#### UART USB-Serial Adapter

If you are using PANDA V1.0 and an Alladin AL-1000 syring pump, you may need to install the following driver to communicate using a USB to RS-232 adapter.

[Download Link](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)

#### GAMRY Potentiostat SDKs and Drivers

If you are using a Gamry potentiostat, you will need to install GAMRY Framwork and associated applications. The python SDK is not required, as it is limited to Python 3.7 which is beyond end-of-life.

You will need to either refer to the media included with your potentiostat purchase or reach out to Gamry instruments. Their website doesn't offer the download for free.

### 3. Choose Your Installation Method

#### Option A: Using UV (Recommended)

a. Install UV:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux
curl -sSf https://astral.sh/uv/install.sh | bash
```

b. Edit `pyproject.toml` to set the path to your Spinnaker Python wheel:

```toml
[tool.uv.sources]
spinnaker-python = {path/to/your/spinnaker_python-wheel.whl}
```

c. Create and activate a virtual environment:

```bash
uv venv panda_sdl --python 3.10

# Windows
.venv\Scripts\activate

# Linux
source .venv/bin/activate
```

d. Install dependencies:

```bash
uv sync --reinstall
```

#### Option B: Using pip

a. Create a virtual environment:

```bash
# Windows
python -m venv panda_sdl
panda_sdl\Scripts\activate

# Linux
python -m venv panda_sdl
source panda_sdl/bin/activate
```

b. Edit `requirements.txt` to set the path to your Spinnaker Python wheel:

```
spinnaker-python @ path/to/your/spinnaker_python-wheel.whl
```

c. Install dependencies:

```bash
pip install -r requirements.txt
```

### 4. Configure the Environment

a. Create a `.env` file in the project root:

```
# Paths
PANDA_SDL_CONFIG_PATH = /path/to/your/config.ini

# Temp DB for pytest
TEMP_DB='0'
```

b. Create a config file using this template:

```ini
[PANDA]
version = 0.0
unit_id = 0
unit_name = ""

[DEFAULTS]
blowout_volume = 40.0
drip_stop_volume = 5.0
pipette_purge_volume = 20.0
pumping_rate = 0.3

[OPTIONS]
testing = True
random_experiment_selection = False
use_slack = False
precision = 6

[LOGGING]
file_level = DEBUG
console_level = ERROR

[GENERAL]
protocols_dir = panda_experiment_protocols
generators_dir = panda_experiment_generators

[TESTING]
testing_db_type = sqlite
testing_db_address = test_db.db
testing_db_user = None
testing_db_password = None
logging_dir = logs_test
data_dir = data\data_test

[PRODUCTION]
production_db_type = sqlite
production_db_address = test_db.db
production_db_user = 
production_db_password = 
logging_dir = 
data_dir = 

[SLACK]
slack_token = 
slack_conversation_channel_id = 
slack_alert_channel_id = 
slack_data_channel_id = 
slack_test_conversation_channel_id = 
slack_test_alert_channel_id = 
slack_test_data_channel_id = 

[MILL]
port = COM4
baudrate = 115200
timeout = 10
config_file = mill_config.json

[PUMP]
port = COM5
baudrate = 19200
timeout = 10
syringe_inside_diameter = 4.600
syringe_capacity = 1
max_pumping_rate = 0.654
units = MM

[CAMERA]
camera_type = webcam 
webcam_id = 0  
webcam_resolution_width = 1280
webcam_resolution_height = 720

[ARDUINO]
port = COM3
baudrate = 115200
timeout = 10

[POTENTIOSTAT]
model = emstat
port = 
firmware_path =

[PIPETTE]
pipette_type = WPI


[TOOLS]
offsets = [
    {
        "name": "center",
        "x": 0.0,
        "y": -5.5,
        "z": 0.0
    },
    {
        "name": "pipette",
        "x": -117.13,
        "y": -11.75,
        "z": 100.0
    },
    {
        "name": "electrode",
        "x": 48.35,
        "y": -11.77,
        "z": 87.0
    },
    {
        "name": "decapper",
        "x": -64.27,
        "y": -12.5,
        "z": 62.0
    },
    {
        "name": "lens",
        "x": 0.0,
        "y": -5.5,
        "z": 0.0
    },
    {
        "name": "mill",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
    }
    ]

[P300]
max_pipetting_rate = 50.0
pipette_capacity = 300
```

## Setting up Slack [Optional]

To obtain a token for your own SlackBot you will need to follow the [instructions](https://api.slack.com/quickstart) from Slack on making a Slack App.

### Scopes

Request both read and write scopes.

### Access Token

Get the access token from the OAuth & Permissions page and add it to your ini file.

### Channel IDs

For each channel that you want the app to have access to you first need to add the bot to the channel, and then find the channel ID by going to that channel in the Slack app, click the channel name at the top, and scroll to the bottom of the pop-up. There will be Channel ID: ######### and a copy button. Repeat for each channel and add the appropriate code in the ini file.

## Running Your First Experiment

### 1. Start the PANDA System

To start the PANDA system, run:

```bash
python main.py
```

This will launch the main menu interface where you can interact with the system.

Depending on how you configured your config file, the system will prompt you to create any missing directories, or databases.

### 2. Using the Main Menu

The main menu provides various options for controlling the system. Here are some basic commands:

- Press `7` to test the camera (good first test)
- Press `8` to check all instrument connections
- Press `t` to toggle testing mode (uses mock instruments, good for validating protocols run virtually)
- Press `q` to exit the program

Detailed descriptions of each command can be found in [Main Menu Reference](Main-Menu-Reference.md)

### 3. Running a Demo Protocol

To run a demo experiment:

1. Navigate to the main menu
2. Press `4` then `1` to access the experiment generator menu
3. Select one of the available demo generators
4. Press `1` to run the queue of generated experiments

## Next Steps

Now that you've set up your environment and run your first experiment, you can:

- Learn to [write your own protocols](Writing-Protocols.md)
- Create [custom experiment generators](Creating-Generators.md)
- Explore the [main menu options](Main-Menu-Reference.md) in more detail

## Troubleshooting

If you encounter issues during installation or running:

- Check the logs in the `logs_test/` directory
- Ensure all hardware is properly connected
- Verify your config.ini file is correctly configured
- Make sure your Python version is exactly 3.10

For more detailed information, refer to the [End User Manual](../documentation/end_user_manual.md).
