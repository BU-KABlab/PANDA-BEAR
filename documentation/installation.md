<!-- title: PANDA SDL Installation Instructions -->

# [Construction](constructions.md) | Installation | [End User Manual](end_user_manual.md) | [Dev User Manual](developer_manual.md) | [Contents](user_manual.md)

# Installation

Clone the repository to a directory on your machine. You may do this graphically from GitHub, or use the commandline.

[GitHub Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

**Using the CLI**

You may need to install git on your device first - [heres how](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

`git clone -b <branch> <remote_repo>`

Example:

`git clone -b my-branch git@github.com:user/myproject.git`

For the PANDA SDL choose the `releases` branch.

# 1. Drivers and SDKs

## FLIR SDK

This system uses a FLIR camera and requires their proprietary SDK which you can obtain for free from their website.

### Where to find the SDK files and examples

Spinnaker is proprietary software made by FLIR and as such cannot be included in the repository. To use the `imaging` module you must have installed both the Spinnaker SDK and the Python SDK in your chosen environment.

Downloading is free but you will need to make an account: <https://www.flir.com/products/spinnaker-sdk/>.

Download both the 4.0 version of the Full Spinnaker SDK as well as the Python SDK that matches your OS and architecture. For example: Windows AMD which is the same as Windows x86. Rasperry Pis are ARM devices.

Install the SDK to your system (you do not need the developer version) to allow for using the Python SDK with this project.

Copy the full path to the python SDK `.whl` file.

Might look something like:

`C:\Users\<your name>\Downloads\spinnaker_python-4.0.#.###-cp310-cp310-win_amd64\spinnaker_python-4.0.#.###-cp310-cp310-win_amd64.whl`

Note: The location doesn't actually matter (could be on your D: drive) so long as you can provide the full path. Your exact version might have slightly different version numbers but so long as the major version is the same it should work.

### Examples

The Linux SDKs do not come with examples, download the Windows or Mac zip files and extract the "Examples" folder.

## UART USB-Serial Adapter

If you are using PANDA V1.0 and an Alladin AL-1000 syring pump, you may need to install the following driver to communicate using a USB to RS-232 adapter.

[Download Link](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)

## GAMRY Potentiostat SDKs and Drivers

If you are using a Gamry potentiostat, you will need to install GAMRY Framwork and associated applications. The python SDK is not required, as it is limited to Python 3.7 which is beyond end-of-life.

You will need to either refer to the media included with your potentiostat purchase or reach out to Gamry instruments. Their website doesn't offer the download for free.

# 2. Setting Up Your Python Environment

**[UV](https://docs.astral.sh/uv/)** by Astral is highly recommended (along with ruff) but you can also use `pip` to setup your environment.

Jump to [Using UV](#option-a-using-uv)
Jump to [Useing PIP](#option-b-using-pip)

## Option A: Using `UV`

### Installing UV

To quickly install, you may enter the following into a PowerShell Terminal:

`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Following the installation, check the terminal for instructions to either restart or run another command (the Powershell command will begin with $).

## Provide path to Spinnaker SDK

After installing UV, navigate to the directory you copied the project repository to.

Edit `pyproject.toml` with a text editor to change the `[tool.uv.sources]` section. You will need to provide the path between the `{}` to the Spinnaker Python `.whl` that you downloaded earlier (you did do part 1 right?).

```toml
[tool.uv.sources]
spinnaker-python = {<your path here>}
```

### Set up Virtual Environment and Install Dependencies

Run the following commands:

`uv venv --python 3.10` -- Creates the virtual environment. You can add a name if you want with `uv venv <name> --python 3.10`

Windows: `.venv\Scripts\activate` | MacOS & Linux `source .venv\bin\activate` -- Activates the environment (change .venv to your custom name if you used one)

The commandline should now begin with `(.venv)` or the custom name you used.

`uv sync --reinstall` -- This will read the `pyproject.toml` file and install dependencies.

### Summary using 'panda_sdl' as environment name

```cmd
> uv venv panda_sdl --python 3.10
> .venv\Scripts\activate
> uv sync
```

[Skip to next step](#env-file)

## Option B Using `PIP`

Use your preferred environment manager to first create a python 3.10 environment.

**Example using builtin Python tools:**

```cmd
python -m venv panda_sdl
```

Windows

```cmd
panda_sdl\Scripts\activate
```

macOS/Linux

```cmd
source panda_sdl/bin/activate
```

The commandline should now begin with `(.venv)` or the custom name you used.

Once activated, and in the folder you copied the project to - open `requirements.txt` with a text editor and update the entry for `spinnaker-python` to be where you have saved the spinnaker python `.whl`.

```requirements
spinnaker-python @ <your file path>/spinnaker_python-4.0.#.###-cp310-cp310-win_amd64/spinnaker_python-4.0.#.###-cp310-cp310-win_amd64.whl
```

Then run the following command:

```cmd
pip install -r requirements.txt
```

## `.env` File

PANDA SDL uses an `.env` file variable to point to the location of your configuration file. This way the config file can live outside of the repository and safely contain keys and tokens.

When first installing PANDA SDL. Create a new file with the name `.env` in the repository's top directory. Paste the following into the file and then update the #TODO field.

```txt
# Paths
PANDA_SDL_CONFIG_PATH = #TODO

# Temp DB for pytest
TEMP_DB='0'

```

## `Config.ini` File

Use this template and place wherever you desire (make sure to update your `.env`). Not all fields are required those that are, are prefilled.

```ini
[PANDA]
version = 0.0
unit_id = 0
unit_name = ""

[DEFAULTS]
air_gap = 40.0
drip_stop_volume = 5.0
pipette_purge_volume = 20.0
pumping_rate = 0.3

[OPTIONS]
testing = True
random_experiment_selection = False
use_slack = False
use_obs = False
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
production_dir = 
production_db_type = sqlite
production_db_address = test_db.db
production_db_user = 
production_db_password = 
logging_dir = 
data_dir = 

[OBS]
obs_host = localhost
obs_password = 
obs_port = 4455
obs_timeout = 3

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

[SCALE]
port = COM6
baudrate = 9600
timeout = 10

[CAMERA]
camera_type = flir 
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

[TOOLS]
offsets = [
    {
        "name": "center",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
    },
    {
        "name": "pipette",
        "x": -99.0,
        "y": 0.0,
        "z": 130.0
    },
    {
        "name": "electrode",
        "x": 22.0,
        "y": 51.0,
        "z": 124.0
    },
    {
        "name": "decapper",
        "x": -73.0,
        "y": 0.0,
        "z": 72.0
    },
    {
        "name": "lens",
        "x": 4.0,
        "y": -1.0,
        "z": 0.0
    }
    ]
```

## Test Your Installation

From the top directory, run: `pytest tests -v`

If all tests pass you are ready to use the PANDA SDL!

## Project Data

PANDA SDL uses a SQL DB to keep track of experiments, parameters, results, and deck objects. The SQLalchemy library is used to interface with which ever database you prefer. By default a SQLite dialect is used, and there is a demonstration SQlite database called `test_db.db` which can be built from running `db_default_structure.sql` then `db_default_data.sql`

## Setting up Slack [Optional]

To obtain a token for your own SlackBot you will need to follow the [instructions](https://api.slack.com/quickstart) from Slack on making a Slack App.

### Scopes

Request both read and write scopes.

### Access Token

Get the access token from the OAuth & Permissions page and add it to your ini file.

### Channel IDs

For each channel that you want the app to have access to you first need to add the bot to the channel, and then find the channel ID by going to that channel in the Slack app, click the channel name at the top, and scroll to the bottom of the pop-up. There will be Channel ID: ######### and a copy button. Repeat for each channel and add the appropriate code in the ini file.

## Setting up OBS [Optional]

PANDA SDL has the ability to use OBS to record the system during experiments.

PANDA SDL uses the integrated OBS webserver for control. To set it up, goto Tools/WebSocket Server Settings and fill in the desired server port and password. Note: The OBS application could be running on a separate computer so long as the two computers are accessible over a network.

The default "Scene" can be found in the repository as `obs_settings/OBS Scene.json` and loaded into OBS. The SlackBot screenshot method relies on the source names to know which video feed to use, so update either one as needed.
