<!-- title: PANDA SDL Installation Instructions -->
# Installation


## .env File
PANDA_SDL only uses one .env variable to point to the location of your configuration file.This way the config file can live outside of the repository and safely contain keys and tokens.

## Config File
There is a default_config.ini under panda_sdl/config which you should use as a template. Not all fields are required. A few fields are less self explanatory or an explanation is too long for a comment:
 - **Protocols vs Experiment Generators**:
    PANDA_SDL defines the list of steps to perform an experiment as a *protocol*.
    Metadata about an experiment, including which protocol to follow, is defined
    in the *ExperimentBase* object which the *experiment_generator* creates. There is usually a one-to-one ratio of protocols to generators unless the protocol is updated but the metadata stays the same.

## Python Dependencies
All PANDA SDL dependencies are listed in the requirements.txt file. If using the devcontainer these are installed for you. If not using the devcontainer, you can add them to your environment with:

```pip install -r requirements.txt```

## Third Party / Proprietary Dependencies
The project depends on one proprietary dependency from Teledyne FLIR for the imaging. See the README file in panda_sdl/flir_camera directory for installation isntructions.

## Setting up Slack [Optional]
To obtain a token for your own SlackBot you will need to follow the [instructions](https://api.slack.com/quickstart) from Slack on making a Slack App.

### Scopes
Request both read and write scopes.

### Access Token
Get the access token from the OAuth & Permissions page and add it to your ini file.

### Channel IDs
For each channel that you want the app to have access to you first need to add the bot to the channel, and then find the channel ID by going to that channel in the Slack app, click the channel name at the top, and scroll to the bottom of the pop-up. There will be Channel ID: ######### and a copy button. Repeat for each channel and add the appropriate code in the ini file.

## Setting up OBS [Optional]

