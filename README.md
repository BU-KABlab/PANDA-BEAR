# PANDA-BEAR

![Static Badge](https://img.shields.io/badge/Python-3.10-blue)
![Static Badge](https://img.shields.io/badge/OS-Windows-blue)
![Static Badge](https://img.shields.io/badge/OS-Debian-maroon)
![Static Badge](https://img.shields.io/badge/Code%20Style-Ruff-purple)
[![Tests](https://github.com/BU-KABlab/PANDA-BEAR/actions/workflows/pytest.yml/badge.svg)](https://github.com/BU-KABlab/PANDA-BEAR/actions/workflows/pytest.yml)

**Polymer Analysis aNd Discovery Array - Bayesian Experimentation for Autonomous Research (PANDA-BEAR)**: An automated system for high-throughput electrodeposition and functional characterization of polymer films.

![PANDA-logo](PANDAlogo.png)

## Overview

PANDA-BEAR is a comprehensive automation framework for conducting high-throughput experiments on polymer thin films. The system integrates multiple laboratory instruments to automate the entire workflow from solution preparation through deposition, characterization, and analysis.

> **Note**: PANDA-BEAR is the successor to PANDA-SDL, with enhanced support for the PANDA-film system and Bayesian optimization capabilities.

## Features

- **Automated Experiment Execution**: Queue and execute batches of experiments with minimal user intervention
- **Multi-Instrument Integration**: Unified control interface for CNC milling, pipetting, potentiostats, cameras, and more
- **Flexible Protocol System**: User-defined experiment protocols and generators
- **Data Management**: Integrated database for experiment tracking and results storage
- **Analysis Framework**: Extensible analysis modules for processing experimental data
- **Command-Line Interface**: Easy-to-use CLI for system control and calibration

## Installation

### Prerequisites

- Python 3.10 (3.11+ not yet supported)
- Operating System: Windows or Linux (Debian-based)
- Virtual environment (recommended)

### Step 1: Install the Library

**Note**: It is recommended that you install into a virtual environment and not globally.

**Choose your installation method:**
- **Install from GitHub** (recommended for end users): Use `pip install git+...` below
- **Clone for development**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup

#### Using UV (Recommended)

```bash
# Install UV if not already installed
# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux:
curl -sSf https://astral.sh/uv/install.sh | bash

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git
```

#### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from repository
pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git
```

### Step 2: Install Hardware-Specific Dependencies

#### FLIR Camera (if using)

1. Download the [FLIR Spinnaker SDK](https://www.flir.com/products/spinnaker-sdk/)
2. Install the system SDK
3. Install the Python SDK (for Python 3.10) into your environment
4. See the SDK documentation for platform-specific instructions

#### Device Drivers

Install drivers for your specific hardware:
- Potentiostat drivers (Gamry, PalmSens)
- USB-serial adapters (CP210x, FTDI, etc.)
- Camera drivers (if not using FLIR)

### Step 3: Database Setup

Initialize the database:

```bash
panda-db-setup
```

This creates the SQLite database with the required schema.

### Step 4: Configuration

1. Create a `.env` file in your working directory:
   ```bash
   PANDA_SDL_CONFIG_PATH=/path/to/your/config.ini
   ```
   > **Note**: The environment variable retains `SDL` naming for backwards compatibility with existing installations.

2. Create a configuration file:
   - Copy `config.ini.example` or `src/panda_shared/config/default_config.ini`
   - Place it at the path specified in `.env`
   - See [CONFIG_FILES.md](CONFIG_FILES.md) for details

3. Update configuration with your hardware settings (ports, calibration values, etc.)

### Step 5: Verify Installation

Run the test suite to verify everything works:

```bash
pytest tests/unit/ -v
```

## Quick Start

**New to PANDA-BEAR?** Start here: [QUICK_START.md](QUICK_START.md)

**Quick commands:**
```bash
# Install from GitHub
pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git

# Set up database
panda-db-setup

# Launch the CLI
panda-cli

# Run tests to verify installation
pytest tests/unit/ -v
```

See the [Getting Started Guide](documentation/01%20Getting-Started.md) for detailed setup instructions.

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

## Documentation

- **[Quick Start Guide](QUICK_START.md)** - Get running in 10 minutes
- [Getting Started Guide](documentation/01%20Getting-Started.md) - Detailed setup
- [Code Architecture](documentation/Code-Architecture.md)
- [Example Scripts](examples/README.md) - Programmatic usage examples
- [Contributing Guidelines](CONTRIBUTING.md)

## Project Structure

```
PANDA-BEAR/
├── src/
│   ├── panda_lib/          # Core library functionality
│   ├── panda_lib_cli/    # Command-line interface
│   ├── panda_lib_db/     # Database setup and management
│   └── panda_shared/     # Shared utilities and configuration
├── panda_experiment_protocols/    # User-defined experiment protocols
├── panda_experiment_generators/   # User-defined experiment generators
├── panda_experiment_analyzers/    # User-defined analysis modules
├── examples/              # Example scripts for programmatic usage
├── tests/                # Test suite
├── documentation/       # Additional documentation
└── scripts/             # Utility scripts
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and setup instructions.

## Running Tests

Verify your installation works by running the test suite:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_specific.py -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more testing options.

## Troubleshooting

### Common Issues

1. **Import errors**: 
   - Ensure you're using Python 3.10: `python --version`
   - Verify virtual environment is activated
   - Reinstall: `pip install --force-reinstall git+https://github.com/BU-KABlab/PANDA-BEAR.git`

2. **Database errors**: 
   - Run `panda-db-setup` to initialize the database
   - Use `panda-db-setup --force` to recreate if corrupted

3. **Hardware connection failures**: 
   - Check device drivers are installed
   - Verify port configurations in your config file
   - Test with `testing = True` in config first (uses mock instruments)

4. **Configuration errors**:
   - Verify `.env` file exists with `PANDA_SDL_CONFIG_PATH` set
   - Check `config.ini` exists at the specified path
   - Review logs in `logs_test/` directory

For more help, please open an issue on GitHub.

## Citation

If you use PANDA-BEAR in your research, please cite the original PANDA publication:

```bibtex
@article{quinn2024panda,
  title = {PANDA: A self-driving lab for studying electrodeposited polymer films},
  author = {Quinn, Harley and Robben, Gregory A. and Zheng, Zhaoyi and Gardner, Alan L. and Werner, Jörg G. and Brown, Keith A.},
  journal = {Materials Horizons},
  volume = {11},
  pages = {5331--5340},
  year = {2024},
  publisher = {Royal Society of Chemistry},
  doi = {10.1039/D4MH00797B}
}
```

### Upcoming Publication

A new publication describing the PANDA-film system and wetting analysis capabilities is forthcoming:

> **"PANDA-film: an automated system for electrodeposition of polymer thin films and their wetting analysis"**
> 
> Quinn, Harley et al. (2026) — *Citation details will be added upon publication.*

## License

This project is licensed under the GPL-2.0 License - see the [LICENSE](LICENSE) file for details.
