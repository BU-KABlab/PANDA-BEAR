# Getting Started with PANDA-SDL

This guide provides step-by-step instructions for installing PANDA-SDL, configuring your environment, and running your first experiment.

**Navigation**: [Home](00-Home.md) | Getting Started | [Writing Protocols](03%20Writing-Protocols.md) | [Creating Generators](02%20Creating-Generators.md) | [Using Analyzers](04%20Using-Analyzers.md)

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Set Up the Database](#4-set-up-the-database)
- [Configure the Environment](#5-configure-the-environment)
- [Setting up Slack](#6-setting-up-slack-optional)
- [Running Your First Experiment](#7-running-your-first-experiment)
- [Next Steps](#8-next-steps)
- [Verifying Your Installation](#9-verifying-your-installation)
- [Troubleshooting](#10-troubleshooting)

## Prerequisites

Before you begin, ensure you have the following:

- **Python 3.10** installed on your system
- A compatible operating system:
  - Windows (recommended due to Gamry potentiostat dependency)
  - Debian-based Linux (with limitations on potentiostat functionality)
- Administrator/sudo privileges for installing system dependencies

## Installation

### 1. Clone the Repository or Install from GitHub

You can either clone the repository for development or install directly from GitHub:

**Option A: Clone for Development**
```bash
git clone https://github.com/BU-KABlab/PANDA-BEAR.git
cd PANDA-BEAR
```

**Option B: Install from GitHub (Recommended for End Users)**
```bash
pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git
```

If installing from GitHub, you can skip to step 3 (Choose Your Installation Method) after creating a virtual environment.

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

## 4. Set Up the Database

Before running experiments, you need to initialize the database:

```bash
panda-db-setup
```

This creates a SQLite database with the required schema. For custom database paths or options, see the [Database Setup README](../src/panda_lib_db/README.md).

## 5. Configure the Environment

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

## 6. Setting up Slack (Optional)

To obtain a token for your own SlackBot you will need to follow the [instructions](https://api.slack.com/quickstart) from Slack on making a Slack App.

### Scopes

Request both read and write scopes.

### Access Token

Get the access token from the OAuth & Permissions page and add it to your ini file.

### Channel IDs

For each channel that you want the app to have access to you first need to add the bot to the channel, and then find the channel ID by going to that channel in the Slack app, click the channel name at the top, and scroll to the bottom of the pop-up. There will be Channel ID: ######### and a copy button. Repeat for each channel and add the appropriate code in the ini file.

## 7. Running Your First Experiment

### Method 1: Using the CLI Menu (Interactive)

1. Start the PANDA system:
   ```bash
   python main.py
   # Or: panda-cli
   ```

2. Enable testing mode (uses mock instruments, no hardware required):
   - Press `t` to toggle testing mode

3. Test the system:
   - Press `7` to test the camera
   - Press `8` to check all instrument connections

4. Run a demo experiment:
   - Press `4` then `1` to access the experiment generator menu
   - Select a generator (e.g., `system_test`)
   - Press `1` to run the queue of generated experiments

Detailed descriptions of each command can be found in [Main Menu Reference](Main-Menu-Reference.md)

### Method 2: Using Python Scripts (Programmatic)

You can run experiments programmatically without the CLI menu:

```bash
# Run the quick start example
python examples/quick_start.py

# Run a specific experiment by ID
python examples/run_experiment.py --experiment-id 1 --testing
```

See the [Examples README](../examples/README.md) for more programmatic usage examples.

### Method 3: Direct Python Code

```python
from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase
from panda_lib.experiment_loop import experiment_loop_worker

# Create and schedule experiment
experiment = EchemExperimentBase(
    experiment_id=scheduler.determine_next_experiment_id(),
    protocol_name="demo",
    well_id="A1",
    wellplate_type_id=4,
    experiment_name="my_experiment",
    project_id=1,
    project_campaign_id=1,
    solutions={},
    ocp=0, baseline=0, cv=0, ca=0,
)
scheduler.schedule_experiments([experiment])

# Run the experiment
experiment_loop_worker(
    use_mock_instruments=True,  # Testing mode
    one_off=True,
    specific_experiment_id=experiment.experiment_id,
)
```

## 8. Next Steps

Now that you've set up your environment and run your first experiment, you can:

- Learn to [write your own protocols](03%20Writing-Protocols.md)
- Create [custom experiment generators](02%20Creating-Generators.md)
- Explore the [main menu options](Main-Menu-Reference.md) in more detail
- Review the [API Reference](API-Reference.md) for available functions

## 9. Verifying Your Installation

Before running experiments, verify your installation works:

```bash
# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html
```

If tests pass, your installation is working correctly!

## 10. Troubleshooting

If you encounter issues during installation or running:

### Common Issues

1. **Database errors**: Run `panda-db-setup --force` to recreate the database
2. **Import errors**: 
   - Verify virtual environment is activated
   - Check Python version is 3.10: `python --version`
   - Reinstall: `pip install --force-reinstall git+https://github.com/BU-KABlab/PANDA-BEAR.git`
3. **Configuration errors**:
   - Check `.env` file exists and `PANDA_SDL_CONFIG_PATH` is set correctly
   - Verify `config.ini` exists at the specified path
   - Check logs in `logs_test/` directory
4. **Hardware connection failures**: 
   - Verify device drivers are installed
   - Check port configurations in `config.ini`
   - Use testing mode first: set `testing = True` in config

### Getting Help

- Check the [Troubleshooting section](../README.md#troubleshooting) in the main README
- Review logs in `logs_test/` directory
- Open an issue on [GitHub](https://github.com/BU-KABlab/PANDA-BEAR/issues)

For additional information, see the [Main Menu Reference](Main-Menu-Reference.md) and [API Reference](API-Reference.md).
