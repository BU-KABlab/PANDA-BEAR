<!-- title: PANDA SDL Installation Instructions -->

# [Construction](constructions.md) | Installation | [End User Manual](end_user_manual.md) | [Dev User Manual](developer_manual.md) | [Contents](user_manual.md)

# Installation

Clone the repository to a directory on your machine. You may do this graphically from GitHub, or use the commandline.

[GitHub Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

**Using the CLI**

You may need to install git on your device first - [heres how](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

```git clone -b <branch> <remote_repo>```

Example:

```git clone -b my-branch git@github.com:user/myproject.git```


# 1. FLIR SDKs

This system uses a FLIR camera and requires their proprietary SDK which you can obtain for free from their website.

## Where to find the SDK files and examples

Spinnaker is proprietary software made by FLIR and as such cannot be included in the repository. To use the `imaging` module you must have installed both the Spinnaker SDK and the Python SDK in your chosen environment.

Downloading is free but you will need to make an account: <https://www.flir.com/products/spinnaker-sdk/>.

Download both the Spinnaker SDK as well as the Python SDK that matches your OS and architecture. Install the SDK to your system to allow for using the Python SDK with this project.

## Examples

The Linux SDKs do not come with examples, download the Windows or Mac zip files and extract the "Examples" folder.

# 2. Setting up your Python Environment

[UV](https://docs.astral.sh/uv/) by Astral is highly recommended (along with ruff) but you can also use `pip` to setup your environment.

## Using `UV`

After installing UV (follow the link above to learn how), using the terminal, navigate to the directory you copied the project repository to.

In `pyproject.toml` under tool.uv.sources you will need to provide the path between the `{}` to the Spinnaker python `.whl` that you downloaded earlier (you did do part 1 right?).

```toml
[tool.uv.sources]
spinnaker-python = {}
```

Run the following commands:

`uv venv --python 3.10` you can add a venv name if you want with `uv venv <name> --python 3.10`

`.venv\Scripts\activate` Activates the environment (change .venv to your .custom_name if you used one)

`uv sync` This will read the `pyproject.toml` file and install dependencies.

### Summary using 'panda_sdl' as environment name

```cmd
> uv venv panda_sdl --python 3.10
> .panda_sdl\Scripts\activate
> uv sync
```

## Using `PIP`

Use your preferred environment manager to first create a python 3.10 environment. 

**Example using built in Python tools:**

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

Once activated, and in the repository directory - open `requirements.txt` and update the entry for `spinnaker-python` to be where you have saved the spinnaker python whl

```requirements
spinnaker-python @ <file_path>/spinnaker_python-4.0.0.116-cp310-cp310-win_amd64/spinnaker_python-4.0.0.116-cp310-cp310-win_amd64.whl
```

Then you may run the following command:
```cmd
pip install -r requirements.txt
```

## `.env` File

PANDA_SDL only uses one `.env` file variables to point to the location of your configuration file. This way the config file can live outside of the repository and safely contain keys and tokens. The `.env` is in the repository's top directory.

## Test Your Installation

From the top directory, run: ```pytest tests -v```

## `Config.ini` File

There is a `default_config.ini` in `shared_utilities/config` which you should use as a template and place wherever you desire so long as you update `.env`. Not all fields are required. A few fields are less self explanatory or an explanation is too long for a comment:

- **Protocols vs Experiment Generators**:

    PANDA_SDL defines the list of steps to perform an experiment as a *protocol*.
    Metadata about an experiment, including which protocol to follow, is defined
    in the *ExperimentBase* (or *ExperimentBase* derived) object which the *experiment_generator* creates. There is usually a one-to-one ratio of protocols to generators unless the protocol is updated but the metadata stays the same.

## Project Data

PANDA SDL uses a SQL DB to keep track of experiments, parameters, results, and deck object. The SQLalchemy library is used to interface with which ever database you prefer. By default a SQLite dialect is used, and there is a demonstration SQlite database called `test_db.db` which can be built from running `db_default_structure.sql` then `db_default_data.sql`

## Setting up Slack [Optional]

To obtain a token for your own SlackBot you will need to follow the [instructions](https://api.slack.com/quickstart) from Slack on making a Slack App.

### Scopes

Request both read and write scopes.

### Access Token

Get the access token from the OAuth & Permissions page and add it to your ini file.

### Channel IDs

For each channel that you want the app to have access to you first need to add the bot to the channel, and then find the channel ID by going to that channel in the Slack app, click the channel name at the top, and scroll to the bottom of the pop-up. There will be Channel ID: ######### and a copy button. Repeat for each channel and add the appropriate code in the ini file.

## Setting up OBS [Optional]

PANDA SDL has the ability to use OBS to  record the system during experiments.

PANDA SDL uses the integrated OBS webserver for control. To set it up, goto Tools/WebSocket Server Settings and fill in the desired server port and password. Note: The OBS application could be running on a separate computer so long as the two computers are accessible over a network.

The default "Scene" can be found in the repository as `obs_settings/OBS Scene.json` and loaded into OBS. The SlackBot screenshot method relies on the source names to know which video feed to use, so update either one as needed.
