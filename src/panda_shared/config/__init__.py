"""
Configuration module for PANDA SDL.
"""

import configparser
import json
import os
from pathlib import Path

def get_config_path():
    """Get the configuration file path from environment variable."""
    from dotenv import load_dotenv
    load_dotenv()
    config_path = os.getenv("PANDA_SDL_CONFIG_PATH")
    if not config_path:
        raise ValueError("PANDA_SDL_CONFIG_PATH environment variable not set")
    return config_path

def load_config():
    """Load and return the configuration."""
    config = configparser.ConfigParser()
    config.read(get_config_path())
    return config
