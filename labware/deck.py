"""
Deck management system for the PANDA instrument.
Provides a grid-based system for positioning labware on the deck.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

logger = logging.getLogger("panda")
definition_schema = [
    "ordering",
    "brand",
    "metadata",
    "dimensions",
    "wells",
    "groups",
    "parameters",
    "namespace",
    "version",
    "schemaVersion",
    "cornerOffsetFromSlot",
]


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
    def from_definition(self, data: dict, position: str) -> "DeckSlot":
        """Create a Well from a dictionary representation."""
        return self(
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
class Dimension:
    """Dimensions of a labware type."""

    xDimension: float
    yDimension: float
    zDimension: float


@dataclass
class Offset:
    """Offset of a labware type in each axis from a primary slot."""

    x: float
    y: float
    z: float


@dataclass
class WellContents:
    """Contents of a well."""

    name: str
    volume: float
    concentration: float


@dataclass
class Well:
    """Represents a single well in a labware."""

    depth: float
    total_liquid_volume: float
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
        # Verify that the data matches the definition schema

        return cls(
            depth=data["depth"],
            total_liquid_volume=data["totalLiquidVolume"],
            shape=data["shape"],
            diameter=data["diameter"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
        )


@dataclass
class Metadata:
    """Metadata of a labware type."""

    displayName: str
    displayCategory: str
    displayVolumeUnits: str
    tags: List[str]


class Labware:
    """Definition of a labware type from a JSON file.

    Attributes:
        name: Name of the labware
        labware_category: Type of labware (wellPlate, vialRack, custom)
        category: Category of the labware
        description: Description of the labware
        brand: Brand of the labware
        brand_id: Brand identifier
        position: Default position on the deck
        reference_point: Reference point for the labware
        dimensions: Dimensions of the labware
        slot_offset: Offset of the labware in the slot
        ordering: Ordering of the wells
        wells: Dictionary of well definitions
        orientation: Orientation of the labware
        metadata: Additional metadata

    """

    def __init__(
        self,
        name: str = None,
        definition: dict = None,
        orientation: int = 0,
    ):
        self.id: str = name
        self.labware_category: LabwareCategory
        self.category: str
        self.description: str
        self.brand: str
        self.brand_id: str
        self.deck_slot_reference: str
        self.deck_slot_reference_coordinates: SlotPosition
        self.deck_slots: List[str]
        self.dimensions: Dimension
        self.slot_offset: Offset
        self.ordering: tuple
        self.order: List[str]
        self.wells: Dict[str:Well]
        self.orientation: int = orientation
        self.metadata: Dict = field(default_factory=dict)
        self.rows: int
        self.columns: int

        if definition:
            ob = self.from_definition(definition)
            self.labware_category = ob.labware_category
            self.brand = ob.brand
            self.brand_id = ob.brand_id
            self.dimensions = ob.dimensions
            self.slot_offset = ob.slot_offset
            self.ordering = ob.ordering
            self.rows = ob.rows
            self.columns = ob.columns
            self.orientation = ob.orientation
            # Flatten the nested list of well IDs
            flat_ordering = [well for row in ob.ordering for well in row if well]

            # Sort alphanumerically by row (letter) then column (number)
            self.order = sorted(
                flat_ordering,
                key=lambda x: (
                    x[0],  # First sort by the letter part
                    int("".join(filter(str.isdigit, x))),  # Then by the numeric part
                ),
            )
            self.wells = ob.wells
            self.metadata = ob.metadata
            self.id = ob.id
            self.category = ob.category

    @staticmethod
    def validate_deck_position(position: str) -> bool:
        """Validate that a position string is a valid deck position."""
        return DeckSlot._validate_position(position)

    @classmethod
    def from_definition(self, data: dict) -> "Labware":
        """Create a LabwareDefinition from a definition dictionary."""
        # Verify that the data matches the definition schema
        if not all(key in data for key in definition_schema):
            logger.error("Invalid labware definition")

        labware = self()

        labware.labware_category = LabwareCategory(data["metadata"]["displayCategory"])
        labware.brand = data["brand"]["brand"]
        labware.brand_id = data["brand"]["brandId"]
        labware.dimensions = Dimension(
            xDimension=data["dimensions"]["xDimension"],
            yDimension=data["dimensions"]["yDimension"],
            zDimension=data["dimensions"]["zDimension"],
        )
        labware.slot_offset = Offset(
            x=data["cornerOffsetFromSlot"]["x"],
            y=data["cornerOffsetFromSlot"]["y"],
            z=data["cornerOffsetFromSlot"]["z"],
        )
        labware.ordering = data["ordering"]
        labware.wells = {k: Well.from_definition(v) for k, v in data["wells"].items()}
        labware.rows = len(data["ordering"])
        labware.columns = len(data["ordering"][0])
        labware.orientation = data.get("orientation", 0)

        labware.metadata = Metadata(
            displayName=data["metadata"]["displayName"],
            displayCategory=data["metadata"]["displayCategory"],
            displayVolumeUnits=data["metadata"]["displayVolumeUnits"],
            tags=data["metadata"]["tags"],
        )
        labware.id = data["parameters"]["loadName"]
        labware.category = data["metadata"]["displayCategory"]

        return labware

    def __str__(self):
        return f"Labware: {self.id}"

    def well_location(self, well_id: str) -> SlotPosition:
        """Return the physical location of a well in the labware."""
        if not self.deck_slot_reference or not self.deck_slot_reference_coordinates:
            logger.error("Labware not placed on the deck")
            return None
        well = self.wells[well_id]
        x_direction_multiplier, y_direction_multiplier = directionMultipliers(
            self.orientation
        )

        reference_slot = self.deck_slot_reference_coordinates
        true_x = reference_slot.x + well.x * x_direction_multiplier
        true_y = reference_slot.y + well.y * y_direction_multiplier
        true_z = reference_slot.z + well.z
        return SlotPosition(x=true_x, y=true_y, z=true_z)


class Deck:
    """
    Represents the physical deck of the instrument with grid-based slots.
    """

    def __init__(self, definition: dict = None):
        """Initialize an empty deck."""
        self.slots: Dict[str, DeckSlot] = {}
        self.dimensions: Dimension = None
        self.labware_positions: Dict[str, List[str]] = {}
        self.calibration_offset: Offset = None
        self.metadata: Metadata = None

        if definition:
            deck = self.from_definition(definition)
            self.slots = deck.slots
            self.dimensions = deck.dimensions
            self.metadata = deck.metadata

    @classmethod
    def from_definition(self, data: dict) -> "Deck":
        """Create a Deck from a definition dictionary."""

        # Verify that the data matches the definition schema
        if not all(key in data for key in definition_schema):
            logger.error("Invalid deck definition")

        deck = self()

        # Create slot objects for all positions defined in the ordering
        for row in data["ordering"]:
            for position in row:
                deck.slots[position] = DeckSlot.from_definition(
                    data["wells"][position], position
                )

        # Set deck dimensions if needed
        if "dimensions" in data:
            deck.dimensions = Dimension(
                xDimension=data["dimensions"]["xDimension"],
                yDimension=data["dimensions"]["yDimension"],
                zDimension=data["dimensions"]["zDimension"],
            )
            logger.info(f"Deck dimensions loaded: {data['dimensions']}")

        # Add any additional deck-specific properties from definition
        if "metadata" in data:
            deck.metadata = Metadata(
                displayName=data["metadata"]["displayName"],
                displayCategory=data["metadata"]["displayCategory"],
                displayVolumeUnits=data["metadata"]["displayVolumeUnits"],
                tags=data["metadata"]["tags"],
            )
            logger.info(f"Deck metadata loaded: {data['metadata']['displayName']}")

        return deck

    def place_labware(
        self, labware: Labware, reference_slot: str | DeckSlot, orientation: int = None
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
        # Check if the labware is already placed
        # if labware.id in self.labware_positions:
        #     logger.error(f"Labware {labware.id} is already placed on the deck")
        #     return False

        # Check if the reference slot is valid
        if not DeckSlot._validate_position(reference_slot):
            logger.error(f"Invalid reference slot: {reference_slot}")
            return False

        if orientation is not None:
            labware.orientation = orientation

        reference_slot = (
            reference_slot
            if isinstance(reference_slot, DeckSlot)
            else self.slots[reference_slot]
        )

        # Calculate the deck positions based on the reference slot and the dimensions and orientation of the labware
        deck_positions = []
        orientation = labware.orientation
        x_dim = labware.dimensions.xDimension  # in mm
        y_dim = labware.dimensions.yDimension  # in mm
        x_dim, y_dim = reorient_coordinates(x_dim, y_dim, orientation)
        # calculate the area of the labware footprint
        # if the orientation is 0 or 2, the x dimension is the width of the labware
        # if the orientation is 0 the footprint grows in the positive x and y directions
        # if the orientation is 2 the footprint grows in the negative x and positive y directions
        # if the orientation is 1 or 3, the x dimension is the length of the labware
        # if the orientation is 1 the footprint grows in the negative x and negative y directions
        # if the orientation is 3 the footprint grows in the positive x and negative y directions
        # starting at the reference_slot position, determine the other slots that the labware will occupy

        reference_coordinates = (reference_slot.x, reference_slot.y)

        x_direction, y_direction = directionMultipliers(orientation)

        # Calculate bounds using the direction multipliers

        bounds_of_x_dimensions = (
            reference_coordinates[0],
            reference_coordinates[0] + (x_dim * x_direction),
        )
        bounds_of_y_dimensions = (
            reference_coordinates[1],
            reference_coordinates[1] + (y_dim * y_direction),
        )

        # Sort the bounds to ensure the lower bound is first
        bounds_of_x_dimensions = sorted(bounds_of_x_dimensions)
        bounds_of_y_dimensions = sorted(bounds_of_y_dimensions)

        for slot in self.slots:
            self.slots[slot].x
            slot_coordinates = (self.slots[slot].x, self.slots[slot].y)
            if (
                slot_coordinates[0]
                >= bounds_of_x_dimensions[
                    0
                ]  # slot is greater than or equal to lower x bound
                and slot_coordinates[0]
                <= bounds_of_x_dimensions[
                    1
                ]  # slot is less than or equal to upper x bound
                and slot_coordinates[1]
                >= bounds_of_y_dimensions[
                    0
                ]  # slot is greater than or equal to lower y bound
                and slot_coordinates[1]
                <= bounds_of_y_dimensions[
                    1
                ]  # slot is less than or equal to upper y bound
            ):
                deck_positions.append(slot)

        # Check if all slots are available
        for position in deck_positions:
            if position not in self.slots:
                logger.error(f"Invalid slot position: {position}")
                return False
            if self.slots[position].occupied:
                logger.error(f"Slot {position} is already occupied")
                return False

        # Place the labware
        labware.deck_slot_reference = reference_slot.position
        labware.deck_slot_reference_coordinates = SlotPosition(
            x=reference_slot.x, y=reference_slot.y, z=reference_slot.z
        )
        labware.deck_slots = deck_positions
        for index, position in enumerate(deck_positions):
            self.slots[position].occupied = True

        self.labware_positions[labware.id] = deck_positions

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

    def get_slots_status(self) -> Dict[str, bool]:
        """
        Return a dictionary containing all slots and their occupied status.

        Returns:
            Dict with slot positions as keys and occupied status (bool) as values
        """
        return {position: slot.occupied for position, slot in self.slots.items()}

    def __str__(self):
        """Return the rows and columns of the deck and the status of each slot."""
        slots = self.get_slots_status()
        slot_status = "\n".join(
            f"{position}: {'occupied' if status else 'empty'}"
            for position, status in slots.items()
        )
        return f"Deck: {len(self.slots)} slots\n{slot_status}"

    def __repr__(self):
        """Return a string representation of the deck as a grid."""
        # Extract all row and column values from slot positions
        rows = sorted(set(pos[0] for pos in self.slots.keys()))
        cols = sorted(set(int(pos[1:]) for pos in self.slots.keys()))

        # Create header row with proper alignment
        result = "    " + " ".join(f"{col:2d}" for col in cols) + "\n"

        # Create separator
        result += "   " + "─" * (len(cols) * 3) + "\n"

        # Create the grid with aligned positions
        for row in rows:
            result += f"{row} │ "
            for col in cols:
                position = f"{row}{col}"
                if position in self.slots:
                    marker = "■" if self.slots[position].occupied else "□"
                    result += f"{marker}  "
                else:
                    result += "   "
            result += "\n"

        return result

    def plot_grid(self, save_path=None):
        """
        Create a visual plot of the deck layout.

        Args:
            save_path: Optional path to save the plot to a file

        Returns:
            The matplotlib figure object
        """
        try:
            import matplotlib.patches as patches
            import matplotlib.pyplot as plt
        except ImportError:
            logger.error(
                "Matplotlib is required for plot_grid(). Install with 'pip install matplotlib'"
            )
            print(
                "Matplotlib is required for plot_grid(). Install with 'pip install matplotlib'"
            )
            return None

        # Extract all row and column values
        rows = sorted(set(pos[0] for pos in self.slots.keys()), reverse=True)
        cols = sorted(set(int(pos[1:]) for pos in self.slots.keys()))

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(len(cols) + 2, len(rows) + 2))
        ax.set_xlim(-0.5, len(cols) + 0.5)
        ax.set_ylim(-0.5, len(rows) + 0.5)

        # Plot grid and slots
        for i, row in enumerate(rows):
            for j, col in enumerate(cols):
                position = f"{row}{col}"
                if position in self.slots:
                    color = "red" if self.slots[position].occupied else "lightgray"
                    rect = patches.Rectangle((j, i), 0.9, 0.9, facecolor=color)
                    ax.add_patch(rect)

                    # Add labware ID if present
                    if self.slots[position].labware_id:
                        ax.text(
                            j + 0.45,
                            i + 0.45,
                            self.slots[position].well_id,
                            ha="center",
                            va="center",
                            fontsize=8,
                            color="white",
                        )

                    # Add position label
                    ax.text(j + 0.45, i + 0.2, position, ha="center", va="center")

        # Add row and column labels
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(cols)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(rows)

        # Add grid lines
        ax.grid(True, linestyle="-", alpha=0.7)

        # Set title
        ax.set_title("Deck Layout")

        # Save if requested
        if save_path:
            plt.savefig(save_path)

        return fig


def directionMultipliers(orientation: int) -> tuple:
    # Define direction multipliers for each orientation
    x_direction = -1 if orientation in [1, 2] else 1
    y_direction = -1 if orientation in [2, 3] else 1

    return x_direction, y_direction


def reorient_coordinates(x: float, y: float, orientation: int) -> tuple:
    # Define direction multipliers for each orientation
    if orientation in [1, 3]:
        x, y = y, x

    return x, y
