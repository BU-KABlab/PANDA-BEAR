"""
This script is used to scan to VISA instruments and return the resource names of the instruments found.
"""

import pyvisa

def scan_visa_instruments():
    """Scan for VISA instruments and return the resource names"""
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    return resources

if __name__ == "__main__":
    print(scan_visa_instruments())