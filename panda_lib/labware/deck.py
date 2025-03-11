"""
Deck management system for the PANDA instrument.
Provides a grid-based system for positioning labware on the deck.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

logger = logging.getLogger("panda")

# Define the grid dimensions
DECK_ROWS = "ABCDEF"
DECK_COLUMNS = range(1, 19)  # 1-18


class DeckSlot:
    """Represents a physical slot on the instrument deck."""

    def __init__(self, position: str):
        """
        Initialize a deck slot.

        Args:
            position: String position in format 'A1', 'B2', etc.
        """
        if not self._validate_position(position):
            raise ValueError(f"Invalid deck position: {position}")

        self.position = position
        self.row = position[0]
        self.column = int(position[1:]) if len(position) > 1 else None
        self.occupied = False
        self.labware_id = None

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

        return row in DECK_ROWS and col in DECK_COLUMNS

    def __repr__(self):
        status = "occupied" if self.occupied else "empty"
        return f"<DeckSlot {self.position} ({status})>"


class LabwareType(Enum):
    """Types of labware supported by the system."""

    WELLPLATE = "wellplate"
    VIAL_HOLDER = "vial_holder"
    CUSTOM = "custom"


@dataclass
class DeckPosition:
    """Physical coordinates of a position on the deck."""

    x: float
    y: float
    z: float


@dataclass
class LabwareDefinition:
    """Definition of a labware type from a JSON file."""

    name: str
    labware_type: LabwareType
    category: str
    description: str
    dimensions: Dict[str, float]
    reference_point: Dict[str, float]
    wells: Dict
    orientation: int = 0
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "LabwareDefinition":
        """Create a LabwareDefinition from a dictionary."""
        return cls(
            name=data["metadata"]["name"],
            labware_type=LabwareType(data["metadata"]["type"]),
            category=data["metadata"]["category"],
            description=data["metadata"].get("description", ""),
            dimensions=data["dimensions"],
            reference_point=data["reference_point"],
            wells=data["wells"],
            metadata={
                k: v
                for k, v in data["metadata"].items()
                if k not in ["name", "type", "category", "description"]
            },
        )


class Deck:
    """
    Represents the physical deck of the instrument with grid-based slots.
    """

    def __init__(self):
        """Initialize an empty deck."""
        self.slots: Dict[str, DeckSlot] = {}
        self.labware_positions: Dict[str, List[str]] = {}
        self.occupied = False
        self.labware_id = None
        self.labware_type = None

        # Initialize all slots
        for row in DECK_ROWS:
            for col in DECK_COLUMNS:
                position = f"{row}{col}"
                self.slots[position] = DeckSlot(position)

        self.calibration_offset = DeckPosition(0.0, 0.0, -200.0)

    def place_labware(
        self, labware_id: LabwareDefinition, deck_positions: List[str]
    ) -> bool:
        """
        Place labware on the deck at the specified slots.

        Example:
        deck.place_labware('plate1', ['A1', 'A2', 'A3'])

        Args:
            labware_id: Unique identifier for the labware
            slot_positions: List of slot positions to occupy

        Returns:
            True if placement successful, False otherwise
        """
        # Check if all slots are available
        for position in deck_positions:
            if position not in self.slots:
                logger.error(f"Invalid slot position: {position}")
                return False
            if self.slots[position].occupied:
                logger.error(f"Slot {position} is already occupied")
                return False

        # Place the labware
        for position in deck_positions:
            self.slots[position].occupied = True
            self.slots[position].labware_id = labware_id

        # self.labware_positions[labware_id] = deck_positions
        return True

    def remove_labware(self, labware_id: str) -> bool:
        """
        Remove labware from the deck.

        Args:
            labware_id: Unique identifier for the labware

        Returns:
            True if removal successful, False otherwise
        """
        if labware_id not in self.labware_positions:
            logger.error(f"Labware {labware_id} not found on deck")
            return False

        for position in self.labware_positions[labware_id]:
            self.slots[position].occupied = False
            self.slots[position].labware_id = None

        del self.labware_positions[labware_id]
        return True

    def get_labware_slots(self, labware_id: str) -> List[str]:
        """Get the slots occupied by a labware."""
        return self.labware_positions.get(labware_id, [])

    def calculate_labware_coordinates(
        self, labware_definition: LabwareDefinition, slot_position: str
    ) -> DeckPosition:
        """
        Calculate the absolute coordinates of a labware based on its slot position.

        Args:
            labware_definition: The labware definition
            slot_position: The reference slot position

        Returns:
            The absolute coordinates for the labware
        """
        # This would convert a slot position (e.g., 'A1') to physical coordinates
        # For now, using placeholder values

        # Row offset (A=0, B=1, etc.)
        row_offset = ord(slot_position[0]) - ord("A")
        # Column offset
        col_offset = int(slot_position[1:]) - 1

        slot_width = 10  # mm (example - x dimension of a standard labware)
        slot_height = 10  # mm (example - y dimension of a standard labware)

        # Calculate position based on slot and labware reference point
        orientation = labware_definition.orientation
        if orientation == 0:
            x_dim = labware_definition.dimensions["y"]
            y_dim = labware_definition.dimensions["x"]
            # Row offset (A=0, B=1, etc.)
            col_offset = ord(slot_position[0]) - ord("A")
            # Column offset
            row_offset = int(slot_position[1:]) - 1
        elif orientation == 1:
            x_dim = labware_definition.dimensions["x"]
            y_dim = labware_definition.dimensions["y"]
            # Row offset (A=0, B=1, etc.)
            row_offset = ord(slot_position[0]) - ord("A")
            # Column offset
            col_offset = int(slot_position[1:]) - 1
        elif orientation == 2:
            x_dim = labware_definition.dimensions["y"]
            y_dim = labware_definition.dimensions["x"]
            # Row offset (A=0, B=1, etc.)
            col_offset = ord(slot_position[0]) - ord("A")
            # Column offset
            row_offset = int(slot_position[1:]) - 1
        else:
            x_dim = labware_definition.dimensions["x"]
            y_dim = labware_definition.dimensions["y"]
            # Row offset (A=0, B=1, etc.)
            row_offset = ord(slot_position[0]) - ord("A")
            # Column offset
            col_offset = int(slot_position[1:]) - 1

        x = (col_offset * slot_width) + x_dim + self.calibration_offset.x
        y = (row_offset * slot_height) + y_dim + self.calibration_offset.y
        z = labware_definition.reference_point["z"] + self.calibration_offset.z

        return DeckPosition(x, y, z)

    def calculate_well_coordinates(
        self, labware_definition: LabwareDefinition, slot_position: str, well_id: str
    ) -> DeckPosition:
        """
        Calculate the absolute coordinates of a specific well in a labware.

        Args:
            labware_definition: The labware definition
            slot_position: The reference slot position
            well_id: The well identifier (e.g., 'A1', 'B2')

        Returns:
            The absolute coordinates for the well
        """
        labware_pos = self.calculate_labware_coordinates(
            labware_definition, slot_position
        )

        # Extract well grid information
        wells = labware_definition.wells
        rows = wells["grid"]["rows"]
        cols = wells["grid"]["columns"]

        # Calculate well position
        well_row = ord(well_id[0]) - ord("A")
        well_col = int(well_id[1:]) - 1

        if well_row >= rows or well_col >= cols:
            raise ValueError(
                f"Well {well_id} is outside the grid dimensions ({rows}×{cols})"
            )

        # Calculate coordinates using well spacing and offsets
        x = labware_pos.x + wells["offset"]["x"] + (well_col * wells["spacing"]["x"])
        y = labware_pos.y + wells["offset"]["y"] + (well_row * wells["spacing"]["y"])
        z = labware_pos.z

        return DeckPosition(x, y, z)

    def get_slots_status(self) -> Dict[str, bool]:
        """
        Return a dictionary containing all slots and their occupied status.

        Returns:
            Dict with slot positions as keys and occupied status (bool) as values
        """
        return {position: slot.occupied for position, slot in self.slots.items()}

    def __str__(self):
        slots = self.get_slots_status()
        return f"Deck slots: {slots}"
