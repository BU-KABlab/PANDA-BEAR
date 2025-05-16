# PANDA-SDL

![Static Badge](https://img.shields.io/badge/Python-3.10-blue)
![Static Badge](https://img.shields.io/badge/OS-Windows-blue)
![Static Badge](https://img.shields.io/badge/OS-Debian-maroon)
![Static Badge](https://img.shields.io/badge/Code%20Style-Ruff-purple)
[![Tests](https://github.com/BU-KABlab/panda-bear/actions/workflows/pytest.yml/badge.svg)](https://github.com/BU-KABlab/panda-bear/actions/workflows/pytest.yml)

Polymer analysis and discovery array (PANDA) self-driving lab (SDL): an automated system for high-throughput electrodeposition and functional characterization of polymer films

![PANDA-logo](https://github.com/BU-KABlab/PANDA-SDL/blob/2c1d91d546d233a9af88f7912e32f243253305e5/PANDAlogo.png)

## Usage

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/BU-KABlab/PANDA-SDL.git
   cd PANDA-SDL
   ```

2. **Install FLIR Spinnaker SDK (Required for camera operations):**
   - Download the SDK from [FLIR's website](https://www.flir.com/products/spinnaker-sdk/)
   - Install both the system SDK and Python SDK (for Python 3.10)
   - Note the path to your Python wheel file (.whl)

3. **Choose your preferred installation method:**

   #### Option A: Using UV (Recommended)
   
   a. Install UV:
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Linux/macOS
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
   
   # Linux/macOS
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
   
   # Linux/macOS
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

4. **Configure the environment:**
   
   a. Create a `.env` file in the project root:
   ```
   # Paths
   PANDA_SDL_CONFIG_PATH = /path/to/your/config.ini
   
   # Temp DB for pytest
   TEMP_DB='0'
   ```
   
   b. Create a config file using the template in `shared_utilities/config/default_config.ini`


For detailed information on configuration, usage, and development, see the [documentation](documentation/user_manual.md).

## Instruments

- [Genmitsu PROVerXL 4030 CNC Router](https://www.sainsmart.com/products/genmitsu-proverxl-4030-cnc-router-with-carveco-maker-subscription)
- [WPI Aladin Syringe Pump - Model A-1000](https://www.wpiinc.com/var-al1000hp-aladdin-single-syringe-pump-high-pressure)
- [Gamry Potentiostat Interface 1010E](https://www.gamry.com/potentiostats/interface-1010e-potentiostat/)
- [FLIR grasshopper3 USB](https://www.flir.com/products/grasshopper3-usb3/)
- [Edmunds Optics 55mm Focal Length Partially Telecentric Video Lens](https://www.edmundoptics.com/p/55mm-focal-length-partially-telecentric-video-lens/10573/)
- [Electroluminescent Panel](https://www.technolight.com/product/4-x-6-inch-uv-fade-resistant-white-rectangle-electroluminescent-el-light-panel/)

## Consumables

- [PDMS Gasket](https://cad.onshape.com/documents/8f40aa9641f7f1039e816474/w/adf97a8228dac96fc46992ed/e/9cba4213e4509f8c1b8e8175)
- [ITO-coated Glass Substrate]()
- [20 mL Stock Vials](https://www.fishersci.com/shop/products/clear-voa-glass-vials-0-125in-septa/12-100-112)
- [200 µl Pipette tips]()

## Designs

- [Instrument Holder](https://cad.onshape.com/documents/c75fe6bc68ee2746309c067f/w/80942d9f5953df01d216df22/e/fce6103128a9bdf7b907dcd4)
- [Tubing to Pipette Adaptor](https://github.com/erasmus95/PANDA-BEAR/blob/main/3d-prints/Adapter_v3_fine.stl)
- [Substrate Holder](https://cad.onshape.com/documents/ccde1516ba2f6a9f288ba4a5/w/6078df451920f962c99dc5d0/e/e23eb57422b3a293c7468839)
- [Vial tube rack](https://github.com/erasmus95/PANDA-BEAR/blob/main/3d-prints/TubeRack_2mLx10_v1_scaled.stl)

## Software

- [Python 3.10](https://www.python.org/)
- [Anaconda](https://www.anaconda.com/)
- [Slack SDK](https://slack.dev/python-slack-sdk/)
- [Silicon Labs CP210x_Universal_Windows_Driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)
- [FlyCapture SDK](https://www.flir.com/products/flycapture-sdk/)
- [Open Broadcast Software](https://obsproject.com/)

## Team

- Harley Quinn
- Gregory Robben
- Zhaoyi Zhang
- Alan Gardner
- Dr. Jörg G. Werner
- Dr. Keith Brown

## License

This project is licensed under the GPL2 License - see the LICENSE file for details.
