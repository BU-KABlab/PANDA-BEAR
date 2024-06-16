"""Licenses of required packages"""

import pkg_resources
import prettytable


def get_pkg_license(pkg):
    """Get the license of a package."""
    try:
        lines = pkg.get_metadata_lines("METADATA")
    except:
        lines = pkg.get_metadata_lines("PKG-INFO")

    for line in lines:
        if line.startswith("License:"):
            return line[9:]
    return "(Licence not found)"


def print_packages_and_licenses():
    """Print the packages and their licenses."""
    t = prettytable.PrettyTable(["Package", "License"])
    for pkg in sorted(pkg_resources.working_set, key=lambda x: str(x).lower()):
        t.add_row((str(pkg), get_pkg_license(pkg)))
    print(t)


if __name__ == "__main__":
    print_packages_and_licenses()
