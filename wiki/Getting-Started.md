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

### 2. Install FLIR Spinnaker SDK

The PANDA system uses FLIR cameras for imaging. Install the Spinnaker SDK:

1. Download the SDK from [FLIR's website](https://www.flir.com/products/spinnaker-sdk/)
2. Install both the system SDK and Python SDK (for Python 3.10)
3. Note the path to your Python wheel file (.whl)

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

b. Create a config file using the template in `panda_shared/config/default_config.ini`

## Running Your First Experiment

### 1. Start the PANDA System

To start the PANDA system, run:

```bash
python main.py
```

This will launch the main menu interface where you can interact with the system.

### 2. Using the Main Menu

The main menu provides various options for controlling the system. Here are some basic commands:

- Press `7` to test the camera (good first test)
- Press `8` to check all instrument connections
- Press `t` to toggle testing mode (recommended for first-time users)
- Press `q` to exit the program

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
