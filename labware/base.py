"""
Base classes and utilities for the PANDA labware system.
Contains core classes that don't depend on Pydantic validation.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("panda")


class LabwareCategory(Enum):
    """Types of labware supported by the system."""

    DECK = "deck"
    WELLPLATE = "wellPlate"
    VIAL_RACK = "vialRack"
    CUSTOM = "custom"


@dataclass
class SlotPosition:
    """Physical coordinates of a position on the deck."""

    x: float
    y: float
    z: float


@dataclass
class WellContents:
    """Contents of a well."""

    name: str
    volume: float
    concentration: float


class DeckSlot:
    """Represents a physical slot on the instrument deck."""

    def __init__(
        self,
        position: str,
        row: str,
        column: int,
        shape: str,
        diameter: float,
        x: float,
        y: float,
        z: float,
    ):
        """
        Initialize a deck slot.

        Args:
            position: String position in format 'A1', 'B2', etc.
        """
        self.position: str = position
        self.row: str = row
        self.column: int = column
        self.occupied = False
        self.labware_id = None
        self.shape: str = shape
        self.diameter: float = diameter
        self.x: float = x
        self.y: float = y
        self.z: float = z

    @classmethod
    def from_definition(cls, data: dict, position: str) -> "DeckSlot":
        """Create a DeckSlot from a well definition."""
        return cls(
            position=position,
            row=position[0],
            column=int(position[1:]) if len(position) > 1 else None,
            shape=data["shape"],
            diameter=data["diameter"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
        )

    @staticmethod
    def _validate_position(position: str) -> bool:
        """Validate that a position string is in the correct format."""
        if not position or len(position) < 2:
            return False

        row = position[0].upper()
        try:
            col = int(position[1:])
        except ValueError:
            return False

        if isinstance(row, str) and len(row) > 2 or col < 1:
            return False

        return True

    def __repr__(self):
        status = "occupied" if self.occupied else "empty"
        return f"<DeckSlot {self.position} ({status})>"

    def to_well_definition(self) -> dict:
        """Convert the DeckSlot to a dictionary representation."""
        return {
            "depth": self.z,
            "total_liquid_volume": None,
            "shape": self.shape,
            "diameter": self.diameter,
            "x": self.x,
            "y": self.y,
            "z": self.z,
        }


@dataclass
class Well:
    """Represents a single well in a labware."""

    depth: float
    total_liquid_volume: Optional[float]
    shape: str
    diameter: float
    x: float
    y: float
    z: float
    volume: float = 0.0
    contamination: int = 0
    contents: WellContents = None

    @classmethod
    def from_definition(cls, data: dict) -> "Well":
        """Create a Well from a dictionary representation."""
        return cls(
            depth=data["depth"],
            total_liquid_volume=data.get("totalLiquidVolume"),
            shape=data["shape"],
            diameter=data["diameter"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
        )

    def dict(self) -> dict:
        """Convert the Well to a dictionary representation."""
        return {
            "depth": self.depth,
            "totalLiquidVolume": self.total_liquid_volume,
            "shape": self.shape,
            "diameter": self.diameter,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "volume": self.volume,
            "contamination": self.contamination,
        }


def direction_multipliers(orientation: int) -> tuple:
    """
    Define direction multipliers based on orientation.

    Args:
        orientation: Integer 0-3 representing rotation in 90 degree increments
                    (0 = 0°, 1 = 90°, 2 = 180°, 3 = 270°)

    Returns:
        Tuple of (x_direction, y_direction) multipliers
    """
    x_direction = -1 if orientation in [1, 2] else 1
    y_direction = -1 if orientation in [2, 3] else 1
    return x_direction, y_direction


def reorient_coordinates(x: float, y: float, orientation: int) -> tuple:
    """
    Reorient coordinates based on orientation.

    Args:
        x: X coordinate
        y: Y coordinate
        orientation: Integer 0-3 representing rotation in 90 degree increments

    Returns:
        Tuple of reoriented (x, y) coordinates
    """
    if orientation in [1, 3]:
        x, y = y, x
    return x, y
