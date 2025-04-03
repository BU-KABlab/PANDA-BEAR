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


def get_port_manufacturers()->dict[str:str]:
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


__all__ = [
    "get_ports",
    "get_port_names",
    "get_port_manufacturers",
]
