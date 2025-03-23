"""
Labware definition management for the PANDA system.
Handles loading and validating labware JSON definitions.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .deck import Labware, LabwareCategory


class LabwareRegistry:
    """Registry of all available labware definitions."""

    def __init__(self, definitions_dir: Optional[str] = None):
        """
        Initialize the labware registry.

        Args:
            definitions_dir: Directory containing labware JSON definitions
        """
        self.definitions: Dict[str, Labware] = {}
        self.definitions_dir = Path(
            definitions_dir or os.path.join(os.path.dirname(__file__), "definitions")
        )

        # Create definitions directory if it doesn't exist
        self.definitions_dir.mkdir(parents=True, exist_ok=True)

        # Load all definitions on initialization
        self.load_all_definitions()

    def load_all_definitions(self) -> None:
        """Load all labware definitions from the definitions directory."""
        for json_file in self.definitions_dir.glob("*.json"):
            try:
                self.load_definition(json_file)
            except Exception as e:
                print(f"Error loading definition {json_file}: {e}")

    def load_definition(self, file_path: Path) -> Labware:
        """
        Load a single labware definition from a file.

        Args:
            file_path: Path to the JSON definition file

        Returns:
            The loaded labware definition
        """
        with open(file_path, "r") as f:
            data = json.load(f)

        # definition = Labware.from_definition(data)
        # self.definitions[definition.id] = definition

        definition = data
        self.definitions[data["parameters"]["loadName"]] = data
        return definition

    def get_definition(self, name: str) -> Optional[Labware]:
        """Get a labware definition by name."""
        return self.definitions.get(name)

    def get_all_definitions(self) -> List[Labware]:
        """Get all labware definitions."""
        return list(self.definitions.values())

    def get_by_type(self, labware_type: LabwareCategory) -> List[Labware]:
        """Get all labware definitions of a specific type."""
        return [
            d for d in self.definitions.values() if d.labware_category == labware_type
        ]

    def register_definition(self, definition: Dict) -> Labware:
        """Register a new labware definition from a dictionary."""
        labware_def = Labware.from_definition(definition)
        self.definitions[labware_def.name] = labware_def

        # Save to file
        file_path = self.definitions_dir / f"{labware_def.name}.json"
        with open(file_path, "w") as f:
            json.dump(definition, f, indent=2)

        return labware_def
