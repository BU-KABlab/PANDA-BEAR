# Using the FLIR SDKs

## Where to find the SDK files and exmaples
Spinnaker is proprietary software made by Teledyne FLIR and as such cannot be included in the repository. To use the flir_camera module you must have installed both the Spinnaker SDK and the Python wrapper in your chosen environment.

Downloading is free but you will need to make an account: https://www.flir.com/products/spinnaker-sdk/

Download both the Spinnaker SDK as well as the Python SDK that matches your OS.

## Using the devcontainer
Copy both SDKs into the .devcontainer/installers folder
Open panda_sdl.dockerfile and update the verion of the SDKs accordingly
Ex: spinnaker-4.#.#.###-amd64-pkg-22.##.tar.gz
Note it is not reccomended to use a different major version than Spinnaker 4 or Ubuntu 22

## Examples
The Linux SDKs do not come with examples, download the Windows or Mac zip files and extract the "Examples" folder.