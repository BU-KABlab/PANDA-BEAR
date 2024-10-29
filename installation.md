<!-- title: PANDA SDL Installation Instructions -->
# Installation

## .env File

PANDA_SDL only uses one .env variable to point to the location of your configuration file. This way the config file can live outside of the repository and safely contain keys and tokens.

## Config File

There is a default_config.ini under panda_sdl/config which you should use as a template. Not all fields are required. A few fields are less self explanatory or an explanation is too long for a comment:

- **Protocols vs Experiment Generators**:

    PANDA_SDL defines the list of steps to perform an experiment as a *protocol*.
    Metadata about an experiment, including which protocol to follow, is defined
    in the *ExperimentBase* object which the *experiment_generator* creates. There is usually a one-to-one ratio of protocols to generators unless the protocol is updated but the metadata stays the same.

## Python Dependencies

PANDA SDL depends on Python 3.10 (3.11 does not work due to FLIR's PySpin being capped) All dependencies are listed in the requirements.txt file with the exception of the FLIR library (see Third Party/Proprietary Dependencies). If using the devcontainer these are installed for you. If not using the devcontainer, you can add them to your environment with the following terminal command after navigating to the repository directory:

```pip install -r requirements.txt```


## Third Party / Proprietary Dependencies

The project depends on one proprietary dependency from Teledyne FLIR for the imaging. See the README file in panda_sdl/flir_camera directory for installation isntructions.

## Project Data

PANDA SDL uses sqlalchemy to interface with databases. By default a sqlite dialect is used, and there is a demonstration sqlite database called test_db.db which can be built from running db_default_strucutre.sql then db_default_data.sql

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

PANDA SDL uses the integrated OBS webserver for control. To set it up, goto Tools/WebSocket Server Settings and fill in the desired server port and password. Note: The OBS application could be running on a serperate computer so long as the two computers are accessible over a network.

The default "Scene" can be found in the repository and loaded into OBS. The SlackBot screenshot method relies on the source names to know which video feed to use, so update either one as needed.