# PANDA-SDL

![Static Badge](https://img.shields.io/badge/Python-3.10-blue)
![Static Badge](https://img.shields.io/badge/OS-Windows-blue)
![Static Badge](https://img.shields.io/badge/OS-Debian-maroon)
![Static Badge](https://img.shields.io/badge/Code%20Style-Ruff-purple)
[![Tests](https://github.com/BU-KABlab/panda-bear/actions/workflows/pytest.yml/badge.svg)](https://github.com/BU-KABlab/panda-bear/actions/workflows/pytest.yml)

Polymer analysis and discovery array (PANDA) - self-driving lab (SDL): an automated system for high-throughput electrodeposition and functional characterization of polymer films

![PANDA-logo](https://github.com/BU-KABlab/PANDA-SDL/blob/2c1d91d546d233a9af88f7912e32f243253305e5/PANDAlogo.png)

## Usage

### Installation

1. **Installing the library:**

   **Note**: It is reccomended that you install into a virtual environment and not globally.

   **UV**

   ```bash
   uv add git+https://github.com/BU-KABlab/PANDA-SDL.git
   ```

   **PIP**

   ```bash
   pip install git+https://github.com/BU-KABlab/PANDA-SDL.git
   ```

2. **If using a FLIR camera. Install FLIR Spinnaker SDK (Required for camera operations):**
   - Download the SDK from [FLIR's website](https://www.flir.com/products/spinnaker-sdk/)
   - Install the system SDK
   - Install the Python SDK (for Python 3.10) into your environment. See the README included with the SDK.

3. **Install any device drivers for devices or cables you are using in your set up.**

   These may include:
      - Potentiostat driver
      - usb-serial adapter

## Instruments

- [Genmitsu PROVerXL 4030 CNC Router](https://www.sainsmart.com/products/genmitsu-proverxl-4030-cnc-router-with-carveco-maker-subscription)
- [WPI Aladin Syringe Pump - Model A-1000](https://www.wpiinc.com/var-al1000hp-aladdin-single-syringe-pump-high-pressure)
- [Opentrons OT2 P300](https://opentrons.com/products/single-channel-electronic-pipette-p20)
- [Gamry Potentiostat Interface 1010E](https://www.gamry.com/potentiostats/interface-1010e-potentiostat/)
- [PalmSens EMStat4S](https://www.palmsens.com/product/emstat4s/)
- [FLIR grasshopper3 USB](https://www.flir.com/products/grasshopper3-usb3/)
- [Edmunds Optics 55mm Focal Length Partially Telecentric Video Lens](https://www.edmundoptics.com/p/55mm-focal-length-partially-telecentric-video-lens/10573/)
- [Electroluminescent Panel](https://www.technolight.com/product/4-x-6-inch-uv-fade-resistant-white-rectangle-electroluminescent-el-light-panel/)

## Consumables

- [PDMS Gasket](https://cad.onshape.com/documents/8f40aa9641f7f1039e816474/w/adf97a8228dac96fc46992ed/e/9cba4213e4509f8c1b8e8175)
- [ITO-coated Glass Substrate]()
- [20 mL Stock Vials](https://www.fishersci.com/shop/products/clear-voa-glass-vials-0-125in-septa/12-100-112)
- [200 µl Pipette tips]()
- [Custom Vial Caps](https://github.com/BU-KABlab/PANDA-BEAR/blob/0c87d3690d6859b006e714fc3e648995843cf5f1/documentation/sops/vialcapfabrication.md)

## Designs

- [Instrument Holder/PAW](https://github.com/BU-KABlab/PANDA-BEAR/tree/0c87d3690d6859b006e714fc3e648995843cf5f1/documentation/3D-prints/PAW)
- [Substrate Holder](https://github.com/BU-KABlab/PANDA-BEAR/tree/0c87d3690d6859b006e714fc3e648995843cf5f1/documentation/3D-prints/DeckAccessories)
- [Vial Rack](https://github.com/BU-KABlab/PANDA-BEAR/blob/0c87d3690d6859b006e714fc3e648995843cf5f1/documentation/3D-prints/DeckAccessories/9VialHolder20mL_TightFit.step)
- [Custom Vial Caps](https://github.com/BU-KABlab/PANDA-BEAR/tree/0c87d3690d6859b006e714fc3e648995843cf5f1/documentation/3D-prints/VialCap)
  
## Software

- [Python 3.10](https://www.python.org/)
- [Anaconda](https://www.anaconda.com/)
- [Slack SDK](https://slack.dev/python-slack-sdk/)
- [Silicon Labs CP210x_Universal_Windows_Driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)
- [FlyCapture SDK](https://www.flir.com/products/flycapture-sdk/)
- [Open Broadcast Software](https://obsproject.com/)

## Team

- Dr. Harley Quinn
- Gregory Robben
- Zhaoyi Zhang
- Alan Gardner
- Dr. Jörg G. Werner
- Dr. Keith Brown

## License

This project is licensed under the GPL2 License - see the LICENSE file for details.
