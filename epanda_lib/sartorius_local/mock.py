"""
mock.py
Contains mocks for driver objects for offline testing.

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

"""Contains mocks for driver objects for offline testing."""

import asyncio
from random import choice, random
from typing import Any
from unittest.mock import MagicMock

from .driver import Scale as RealScale


class AsyncClientMock(MagicMock):
    """Magic mock that works with async methods."""

    async def __call__(self, *args, **kwargs):  # type: ignore [no-untyped-def]
        """Convert regular mocks into into an async coroutine."""
        return super().__call__(*args, **kwargs)


class Scale(RealScale):
    """Mocks the Scale driver for offline testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Set up connection parameters with default scale port."""
        super().__init__(*args, **kwargs)
        self.info = {"model": "SIWADCP-1-",
                     "serial": "37454321",
                     "software": "00-37-09",
                     "measurement": "net"}

    async def get(self) -> dict:
        """Get scale reading."""
        await asyncio.sleep(random() * 0.25)
        return {'stable': True,
                'units': choice(['kg', 'lb']),
                'mass': random() * 100.0}

    async def get_info(self) -> dict:
        """Get scale model, serial, and software version numbers."""
        await asyncio.sleep(random() * 0.1)
        return self.info

    async def zero(self) -> None:
        """Tare and zero the scale."""
        await asyncio.sleep(random() * 0.1)
