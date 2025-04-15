from .config.config_print import print_config_values, resolve_config_paths
from .config.config_tools import (
    get_env_var,
    get_repo_path,
    read_config,
    read_data_dir,
    read_logging_dir,
    read_testing_config,
    test,
    write_testing_config,
)
from .log_tools import setup_default_logger


def get_ports():
    """List all available ports"""
    import os

    import serial.tools.list_ports

    if os.name == "posix":
        ports = list(serial.tools.list_ports.grep("ttyUSB"))
    elif os.name == "nt":
        ports = list(serial.tools.list_ports.grep("COM"))
    else:
        raise OSError("Unsupported OS")
    return [port.device for port in ports]


def get_port_names():
    """List all available port names"""
    import os

    import serial.tools.list_ports

    if os.name == "posix":
        ports = list(serial.tools.list_ports.grep("ttyUSB"))
    elif os.name == "nt":
        ports = list(serial.tools.list_ports.grep("COM"))
    else:
        raise OSError("Unsupported OS")
    return [port.name for port in ports]


def get_port_manufacturers() -> dict[str:str]:
    """List all available port manufacturers"""
    import os

    import serial.tools.list_ports

    if os.name == "posix":
        ports = list(serial.tools.list_ports.grep("ttyUSB"))
    elif os.name == "nt":
        ports = list(serial.tools.list_ports.grep("COM"))
    else:
        raise OSError("Unsupported OS")

    manufacturers = {}
    for port in ports:
        manufacturer = port.manufacturer if port.manufacturer else "Unknown"
        manufacturers[port.device] = manufacturer
    return manufacturers


resolve_config_paths()

__all__ = [
    "print_config_values",
    "resolve_config_paths",
    "get_env_var",
    "get_repo_path",
    "read_config",
    "read_testing_config",
    "test",
    "write_testing_config",
    "read_data_dir",
    "read_logging_dir",
    "get_ports",
    "get_port_names",
    "get_port_manufacturers",
    "setup_default_logger",
]
