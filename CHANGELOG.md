# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive repository cleanup and professionalization
- CONTRIBUTING.md with contribution guidelines
- CHANGELOG.md for tracking changes
- Improved .gitignore with better coverage
- Scripts directory for utility scripts

### Changed
- Moved security-sensitive files to please_delete/ directory
- Consolidated configuration file structure
- Improved documentation structure

### Removed
- Duplicate files (slack_bot.py, old code/ directory)
- Unused standalone scripts from root directory
- Security-sensitive data exports

## [2.0] - Current Release

### Features
- Core PANDA SDL functionality
- Hardware drivers for various instruments
- Experiment protocol system
- Analysis framework
- Database integration
- CLI interface

### Hardware Support
- Genmitsu PROVerXL 4030 CNC Router
- WPI Aladin Syringe Pump
- Opentrons OT2 P300 Pipette
- Gamry Potentiostat Interface 1010E
- PalmSens EMStat4S
- FLIR Grasshopper3 USB Camera
- Custom scale integration

### Dependencies
- Python 3.10
- See pyproject.toml for complete dependency list

## [Previous Versions]

Historical changes from earlier versions are not fully documented in this changelog.
For details on earlier development, see the git commit history.
