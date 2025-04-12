"""
Labware definition management for the PANDA system.
Handles loading and validating labware JSON definitions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from .base import (
    LabwareCategory,
    SlotPosition,
    Well,
    direction_multipliers,
)
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
        definition: Union[dict, LabwareDefinition] = None,
        orientation: int = 0,
    ):
        self.id: str = name
        self.labware_category: LabwareCategory
        self.category: str
        self.description: str
        self.brand: str
        self.brand_id: List[str]
        self.deck_slot_reference: str = None
        self.deck_slot_reference_coordinates: SlotPosition = None
        self.deck_slots: List[str] = []
        self.dimensions: Dimensions
        self.cornerOffsetFromSlot: Offset
        self.ordering: List[List[str]]
        self.order: List[str] = []
        self.wells: Dict[str, Well] = {}
        self.orientation: int = orientation
        self.metadata: Metadata = None
        self.rows: int = 0
        self.columns: int = 0
        self.namespace: str = "panda_v2"
        self.version: int = 1
        self.schemaVersion: int = 2
        self.parameters: Parameters = None

        if definition:
            if isinstance(definition, LabwareDefinition):
                # Convert Pydantic model to internal representation
                self._from_pydantic_definition(definition)
            else:
                # Handle dictionary definition
                ob = self.from_definition(definition)
                self._copy_from(ob)

    def _copy_from(self, ob: "Labware") -> None:
        """Copy all attributes from another Labware instance."""
        self.labware_category = ob.labware_category
        self.category = ob.category
        self.brand = ob.brand
        self.dimensions = ob.dimensions
        self.cornerOffsetFromSlot = ob.cornerOffsetFromSlot
        self.ordering = ob.ordering
        self.rows = ob.rows
        self.columns = ob.columns
        self.orientation = ob.orientation
        self.order = ob.order
        self.wells = ob.wells
        self.metadata = ob.metadata
        self.id = ob.id
        self.namespace = ob.namespace
        self.version = ob.version
        self.schemaVersion = ob.schemaVersion
        self.parameters = ob.parameters

    def _from_pydantic_definition(self, definition: LabwareDefinition) -> None:
        """Create a Labware instance from a Pydantic LabwareDefinition."""
        self.labware_category = LabwareCategory(definition.metadata.displayCategory)
        self.brand = definition.brand
        self.dimensions = definition.dimensions
        self.cornerOffsetFromSlot = definition.cornerOffsetFromSlot
        self.ordering = definition.ordering
        self.wells = {
            k: Well.from_definition(v.dict()) for k, v in definition.wells.items()
        }
        self.rows = len(definition.ordering)
        self.columns = len(definition.ordering[0]) if self.rows > 0 else 0
        self.orientation = definition.parameters.orientation
        self.metadata = definition.metadata
        self.id = definition.parameters.loadName
        self.category = definition.metadata.displayCategory
        self.namespace = definition.namespace
        self.version = definition.version
        self.schemaVersion = definition.schemaVersion
        self.parameters = definition.parameters

        # Flatten the nested list of well IDs
        flat_ordering = [well for row in self.ordering for well in row if well]

        # Sort alphanumerically by row (letter) then column (number)
        self.order = sorted(
            flat_ordering,
            key=lambda x: (
                x[0],  # First sort by the letter part
                int("".join(filter(str.isdigit, x))),  # Then by the numeric part
            ),
        )

    @staticmethod
    def validate_deck_position(position: str) -> bool:
        """Validate that a position string is a valid deck position."""
        from .base import DeckSlot

        return DeckSlot._validate_position(position)

    @classmethod
    def from_definition(cls, data: dict) -> "Labware":
        """Create a Labware from a definition dictionary."""
        # Create a Pydantic model from the dictionary to validate

        if isinstance(data, dict):
            # Convert dictionary to LabwareDefinition Pydantic model
            pydantic_def = LabwareDefinition.model_validate(data)
        else:
            pydantic_def = data

        # Create labware instance from validated pydantic model
        labware = cls()
        labware._from_pydantic_definition(pydantic_def)

        return labware

    def to_definition(self) -> LabwareDefinition:
        """Convert the Labware to a LabwareDefinition for serialization."""
        # Convert wells to WellDefinition
        well_defs = {k: self._well_to_definition(v) for k, v in self.wells.items()}

        # Create brand
        brand = Brand(
            brand=self.brand,
            brandId=self.brand_id
            if isinstance(self.brand_id, list)
            else [self.brand_id],
        )

        # Create parameters
        params = (
            self.parameters
            if self.parameters
            else Parameters(loadName=self.id, orientation=self.orientation)
        )

        # Create the LabwareDefinition
        return LabwareDefinition(
            ordering=self.ordering,
            brand=brand,
            metadata=self.metadata,
            dimensions=self.dimensions,
            wells=well_defs,
            parameters=params,
            namespace=self.namespace,
            version=self.version,
            schemaVersion=self.schemaVersion,
            cornerOffsetFromSlot=self.cornerOffsetFromSlot,
        )

    def _well_to_definition(self, well: Well) -> WellDefinition:
        """Convert a Well to a WellDefinition for serialization."""
        return WellDefinition(
            depth=well.depth,
            totalLiquidVolume=well.total_liquid_volume,
            shape=well.shape,
            diameter=well.diameter,
            x=well.x,
            y=well.y,
            z=well.z,
        )

    def save_definition(self, file_path: Optional[str] = None) -> str:
        """
        Save the labware definition to a JSON file.

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
            file_path = registry.definitions_dir / f"{self.id}.json"
        else:
            file_path = Path(file_path)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(file_path, "w") as f:
            json.dump(definition.model_dump(exclude_none=True), f, indent=2)

        logger.info(f"Saved labware definition to {file_path}")
        return str(file_path)

    def __str__(self):
        return f"Labware: {self.id}"

    def well_location(self, well_id: str) -> SlotPosition:
        """Return the physical location of a well in the labware."""
        if not self.deck_slot_reference or not self.deck_slot_reference_coordinates:
            logger.error("Labware not placed on the deck")
            return None
        well = self.wells[well_id]
        x_direction_multiplier, y_direction_multiplier = direction_multipliers(
            self.orientation
        )

        reference_slot = self.deck_slot_reference_coordinates
        true_x = reference_slot.x + well.x * x_direction_multiplier
        true_y = reference_slot.y + well.y * y_direction_multiplier
        true_z = reference_slot.z + well.z
        return SlotPosition(x=true_x, y=true_y, z=true_z)
