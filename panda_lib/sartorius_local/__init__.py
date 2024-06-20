"""
Python driver for Sartorius and Minebea Intec scales.

Distributed under the GNU General Public License v2
Copyright (C) 2019 NuMat Technologies

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""
from typing import Any

from .driver import Scale


def command_line(args: Any = None) -> None:
    """Command line tool exposed through package install."""
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Read scale status.")
    parser.add_argument('address', help="The serial or IP address of the scale.")
    parser.add_argument('-n', '--no-info', action='store_true', help="Exclude "
                        "scale information. Reduces communication overhead.")
    parser.add_argument('-z', '--zero', action='store_true', help="Tares and "
                        "zeroes the scale.")
    args = parser.parse_args(args)

    async def get() -> None:
        async with Scale(address=args.address) as scale:
            if args.zero:
                await scale.zero()
            d = await scale.get()
            if not args.no_info and d.get('on', True):
                d['info'] = await scale.get_info()
            print(json.dumps(d, indent=4))
    asyncio.run(get())


if __name__ == '__main__':
    command_line()
