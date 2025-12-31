# Configuration Files Guide

This document explains the different configuration files in the PANDA-BEAR repository.

## Configuration Files

### 1. `src/panda_shared/config/default_config.ini`

**Purpose**: Default configuration template used by the application code.

**Location**: `src/panda_shared/config/default_config.ini`

**Usage**: This is the canonical default configuration file. The application uses this as a template when generating new configuration files or validating existing ones.

**Default Values**:
- Camera type: FLIR
- Pipette type: WPI
- Tool offsets: Default calibration values

### 2. `config.ini.example`

**Purpose**: Example configuration file for users to copy and customize.

**Location**: Root directory (`config.ini.example`)

**Usage**: Users should copy this file to create their own `panda_sdl_config.ini` (or set `PANDA_SDL_CONFIG_PATH` environment variable to point to their config file).

**Default Values**:
- Camera type: webcam
- Pipette type: OT2
- Tool offsets: Example values (may differ from defaults)

**Note**: This file has slightly different default values than `default_config.ini`. The differences are intentional to show different configuration options.

## Which File Should I Use?

### For New Users

1. **Copy `config.ini.example`** to create your configuration:
   ```bash
   cp config.ini.example panda_sdl_config.ini
   ```

2. **Or use the default** - the application will generate a config from `default_config.ini` if none exists.

3. **Set the environment variable**:
   ```bash
   export PANDA_SDL_CONFIG_PATH=/path/to/your/panda_sdl_config.ini
   ```

### For Developers

- Use `default_config.ini` as the reference for default values
- Update `config.ini.example` if you want to change the example template
- Keep both files in sync for common settings

## Configuration File Structure

Both files contain the same sections:

- `[PANDA]`: System identification
- `[DEFAULTS]`: Default operation parameters
- `[OPTIONS]`: System options and flags
- `[LOGGING]`: Logging configuration
- `[GENERAL]`: General paths and directories
- `[TESTING]`: Test database configuration
- `[PRODUCTION]`: Production database configuration
- `[SLACK]`: Slack integration (optional)
- `[MILL]`: CNC mill configuration
- `[PUMP]`: Syringe pump configuration
- `[CAMERA]`: Camera configuration
- `[ARDUINO]`: Arduino interface configuration
- `[POTENTIOSTAT]`: Potentiostat configuration
- `[PIPETTE]`: Pipette configuration
- `[TOOLS]`: Tool offset calibration values
- `[P300]`: P300 pipette specific settings

## Security Notes

⚠️ **Important**: Never commit your actual configuration file with:
- Real Slack tokens
- Production database passwords
- Sensitive API keys

The `.gitignore` file is configured to exclude `*.ini` files in the root directory, but always verify before committing.

## Environment Variables

The application looks for configuration in this order:

1. `PANDA_SDL_CONFIG_PATH` environment variable
2. `PANDA_TESTING_CONFIG_PATH` (if in testing mode)
3. Default path: `panda_sdl_config.ini` in the repository root

## Troubleshooting

### Config file not found

If you get an error about the config file not being found:

1. Check that `PANDA_SDL_CONFIG_PATH` is set correctly
2. Verify the file exists at the specified path
3. Check file permissions (must be readable and writable)

### Config validation errors

The application will automatically add missing sections/keys from `default_config.ini`. If you see validation errors, check that your config file has all required sections.
