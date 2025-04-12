"""
Deck management system for the PANDA instrument.
Provides a grid-based system for positioning labware on the deck.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from .base import (
    DeckSlot,
    LabwareCategory,
    SlotPosition,
    direction_multipliers,
    reorient_coordinates,
)
from .labware_definition import Labware
from .models import (
    Brand,
    Dimensions,
    LabwareDefinition,
    Metadata,
    Offset,
    Parameters,
    WellDefinition,
)

logger = logging.getLogger("panda")


class Deck:
    """
    Represents the physical deck of the instrument with grid-based slots.
    """

    def __init__(self, definition: Union[dict, LabwareDefinition] = None):
        """Initialize an empty deck."""
        self.slots: Dict[str, DeckSlot] = {}
        self.dimensions: Dimensions = None
        self.labware_positions: Dict[str, List[str]] = {}
        self.calibration_offset: Offset = None
        self.metadata: Metadata = None
        self.deck_slot_reference: str = "A1"
        self.ordering: List[List[str]] = []

        if definition:
            if isinstance(definition, LabwareDefinition):
                self._from_pydantic_definition(definition)
            else:
                deck = self.from_definition(definition)
                self.slots = deck.slots
                self.dimensions = deck.dimensions
                self.metadata = deck.metadata
                self.ordering = deck.ordering

    def _from_pydantic_definition(self, definition: LabwareDefinition) -> None:
        """Initialize deck from a LabwareDefinition Pydantic model."""
        # Create slot objects for all positions defined in the ordering
        for row in definition.ordering:
            for position in row:
                if position:  # Skip empty positions
                    well_def = definition.wells[position]
                    self.slots[position] = DeckSlot(
                        position=position,
                        row=position[0],
                        column=int(position[1:]),
                        shape=well_def.shape,
                        diameter=well_def.diameter,
                        x=well_def.x,
                        y=well_def.y,
                        z=well_def.z,
                    )

        self.ordering = definition.ordering
        self.dimensions = definition.dimensions
        self.metadata = definition.metadata
        logger.info(f"Deck dimensions loaded: {definition.dimensions}")
        logger.info(f"Deck metadata loaded: {definition.metadata.displayName}")

    @classmethod
    def from_definition(cls, data: dict | LabwareDefinition) -> "Deck":
        """Create a Deck from a definition dictionary."""
        # Convert to Pydantic model for validation
        if isinstance(data, dict):
            pydantic_def = LabwareDefinition.model_validate(data)
        else:
            pydantic_def = data
        # Create deck from validated model
        deck = cls()
        deck._from_pydantic_definition(pydantic_def)
        return deck

    def to_definition(self) -> LabwareDefinition:
        """Convert the Deck to a LabwareDefinition for serialization."""
        # Convert slots to WellDefinition objects
        wells = {
            k: WellDefinition(**v.to_well_definition()) for k, v in self.slots.items()
        }

        # Create the LabwareDefinition
        return LabwareDefinition(
            ordering=self.ordering,
            brand=Brand(brand="KABlab", brandId=["PANDA-DECK"]),
            metadata=self.metadata
            or Metadata(
                displayName="KABlab PANDA Deck",
                displayCategory="deck",
                displayVolumeUnits=None,
                tags=[],
            ),
            dimensions=self.dimensions
            or Dimensions(xDimension=480, yDimension=485, zDimension=20),
            wells=wells,
            parameters=Parameters(loadName="kablab_panda_deck", orientation=0),
            namespace="panda_v2",
            version=1,
            schemaVersion=2,
            cornerOffsetFromSlot=Offset(x=0, y=0, z=0),
        )

    def save_definition(self, file_path: Optional[str] = None) -> str:
        """
        Save the deck definition to a JSON file.

        Args:
            file_path: Optional path to save the file. If not provided,
                      uses the default location in the labware registry.

        Returns:
            The path where the file was saved
        """
        definition = self.to_definition()

        if not file_path:
            # Import here to avoid circular import
            from .labware_registry import LabwareRegistry

            # Use default location from LabwareRegistry
            registry = LabwareRegistry()
            version_numbers = []
            # Get all deck definitions
            deck_labwares = registry.get_by_type(LabwareCategory.DECK)

            # Find highest version number
            for labware in deck_labwares:
                if labware.id.startswith("kablab_panda") and "_deck_v" in labware.id:
                    try:
                        version = int(labware.id.split("_v")[-1])
                        version_numbers.append(version)
                    except ValueError:
                        pass

            # Increment version
            new_version = (max(version_numbers) if version_numbers else 0) + 1
            new_name = f"kablab_panda_v2_deck_v{new_version}"

            # Update definition with new name and version
            definition.parameters.loadName = new_name
            definition.version = new_version

            file_path = registry.definitions_dir / f"{new_name}.json"
        else:
            file_path = Path(file_path)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(file_path, "w") as f:
            json.dump(definition.model_dump(exclude_none=True), f, indent=2)

        logger.info(f"Saved deck definition to {file_path}")
        return str(file_path)

    def place_labware(
        self,
        labware: Labware,
        reference_slot: Union[str, DeckSlot],
        orientation: int = None,
    ) -> bool:
        """
        Place labware on the deck at the specified slots.

        Example:
        deck.place_labware(labware, 'A1')

        Args:
            labware: The labware object to place
            reference_slot: Reference slot position or DeckSlot object
            orientation: Optional orientation override (0-3)

        Returns:
            True if placement successful, False otherwise
        """
        # Check if the reference slot is valid
        if isinstance(reference_slot, str) and not DeckSlot._validate_position(
            reference_slot
        ):
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

        reference_coordinates = (reference_slot.x, reference_slot.y)
        x_direction, y_direction = direction_multipliers(orientation)

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
            slot_coordinates = (self.slots[slot].x, self.slots[slot].y)
            if (
                slot_coordinates[0] >= bounds_of_x_dimensions[0]
                and slot_coordinates[0] <= bounds_of_x_dimensions[1]
                and slot_coordinates[1] >= bounds_of_y_dimensions[0]
                and slot_coordinates[1] <= bounds_of_y_dimensions[1]
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
        for position in deck_positions:
            self.slots[position].occupied = True
            self.slots[position].labware_id = labware.id

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
                            self.slots[position].labware_id,
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

    def calculate_slots_from_a1(
        self,
        x_coordinate: float,
        y_coordinate: float,
        z_coordinate: float = -200,
        x_spacing: float = 25,
        y_spacing: float = 45,
    ) -> str:
        """
        Apply the x and y coordinates as the new x,y values of slot A1.

        From this new x,y position, calculate the new positions of all other slots,
        assuming that the slots are arranged in a grid with the specified spacing and
        that A1 is the top-left corner and the rows are lettered alphabetically and the columns are numbered.

        Once calculated, update the x,y coordinates of the slots in the deck definition by creating and registering
        a new deck labware definition with an incremented version number.

        Returns:
            Path to the new deck definition file
        """
        # Calculate the new coordinates for each slot based on the reference slot and spacing
        for position, slot in self.slots.items():
            row_offset = ord(slot.row) - ord("A")
            col_offset = slot.column - 1

            # Calculate new coordinates
            new_x = x_coordinate + col_offset * x_spacing
            new_y = y_coordinate + row_offset * y_spacing

            # Update the slot coordinates
            slot.x = new_x
            slot.y = new_y
            slot.z = z_coordinate
            # Keep the z coordinate the same

        # Save the updated deck definition
        new_file_path = self.save_definition()

        return new_file_path
