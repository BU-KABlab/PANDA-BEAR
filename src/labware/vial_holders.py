from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field

from panda_lib.panda_gantry import Coordinates

from .vials import StockVial, WasteVial


class VialPosition(BaseModel):
    """Defines the properties for a vial position in a holder"""

    index: int
    category: str  # "stock" or "waste"
    name: str = ""
    contents: Dict[str, float] = Field(default_factory=dict)
    volume: float = Field(default=20000.0)
    capacity: float = Field(default=20000.0)


class VialHolderDefinition(BaseModel):
    """Physical dimensions and properties of a vial holder"""

    name: str
    version: str = "1.0.0"
    namespace: str = "panda_vial_holders"

    # Physical dimensions
    num_vials: int = Field(default=8, ge=1, le=12)
    spacing_y: float = Field(default=33.0)  # mm between vials
    vial_diameter: float = Field(default=27.0)  # mm
    vial_height: float = Field(default=57.0)  # mm
    base_thickness: float = Field(default=1.0)  # mm
    dead_volume: float = Field(default=1000.0)  # µL

    # Holder mounting and reference point
    mount_offset_x: float = Field(default=0.0)  # mm from mount to first vial center
    mount_offset_y: float = Field(default=0.0)  # mm from mount to first vial center
    mount_offset_z: float = Field(default=0.0)  # mm from mount to holder base

    # Default vial properties
    default_volume: float = Field(default=20000.0)  # µL
    default_capacity: float = Field(default=20000.0)  # µL

    # Calibration reference points
    reference_point_offset: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )

    # Replace category with vial_positions for mixed holder support
    vial_positions: List[VialPosition] = Field(
        default_factory=lambda: [
            VialPosition(index=i, category="stock") for i in range(8)
        ]
    )

    def get_vial_type(self, index: int) -> str:
        """Get the type of vial at a given position"""
        for pos in self.vial_positions:
            if pos.index == index:
                return pos.category
        raise ValueError(f"No vial defined at index {index}")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "standard_8_vial_holder",
                    "category": "stock",
                    "num_vials": 8,
                    "spacing_y": 33.0,
                    "vial_diameter": 27.0,
                    "vial_height": 57.0,
                }
            ]
        }
    )


@dataclass
class VialHolder:
    """
    Manages a group of vials in a holder, handling calibration and position calculations.
    Supports mixed vial types (stock and waste) within the same holder.
    """

    definition: VialHolderDefinition
    vials: Sequence[Union[StockVial, WasteVial]]
    holder_id: str

    @classmethod
    def from_json(
        cls,
        json_path: Union[str, Path],
        holder_id: str,
        vials: Optional[Sequence[Union[StockVial, WasteVial]]] = None,
    ) -> VialHolder:
        """Create a VialHolder instance from a JSON definition file"""
        with open(json_path, "r") as f:
            holder_def = VialHolderDefinition(**json.load(f))

        if vials is None:
            # Create new vials based on definition's vial positions
            vials = []
            for pos in holder_def.vial_positions:
                vial_class = StockVial if pos.category == "stock" else WasteVial
                vial = vial_class(
                    f"{holder_id}_{pos.index}",
                    create_new=True,
                    height=holder_def.vial_height,
                    radius=holder_def.vial_diameter / 2,
                    volume=pos.volume,
                    capacity=pos.capacity,
                    dead_volume=holder_def.dead_volume,
                    base_thickness=holder_def.base_thickness,
                    name=pos.name or f"{holder_id}_{pos.index}",
                    contents=pos.contents,
                )
                vials.append(vial)

        return cls(holder_def, vials, holder_id)

    def save_definition(self, path: Union[str, Path]):
        """Save the holder definition to a JSON file"""
        with open(path, "w") as f:
            json.dump(self.definition.model_dump(), f, indent=2)

    def get_vial_position(self, vial_index: int) -> Coordinates:
        """Calculate the position of a vial based on the reference vial"""
        if not 0 <= vial_index < self.definition.num_vials:
            raise ValueError(f"Invalid vial index {vial_index}")

        ref_vial = self.vials[0]
        ref_coords = ref_vial.coordinates

        return Coordinates(
            ref_coords.x,
            ref_coords.y - (vial_index * self.definition.spacing_y),
            ref_coords.z,
        )

    def recalculate_positions(self):
        """Update all vial positions based on the reference vial"""
        for i, vial in enumerate(self.vials):
            if i == 0:  # Skip reference vial
                continue
            new_pos = self.get_vial_position(i)
            vial.vial_data.coordinates = {
                "x": new_pos.x,
                "y": new_pos.y,
                "z": new_pos.z,
            }
            vial.save()

    def calibrate_reference_vial(self, new_coordinates: Coordinates):
        """Update the reference vial position and recalculate other positions"""
        ref_vial = self.vials[0]
        ref_vial.vial_data.coordinates = {
            "x": new_coordinates.x,
            "y": new_coordinates.y,
            "z": new_coordinates.z,
        }
        ref_vial.save()
        self.recalculate_positions()

    def get_all_coordinates(self) -> List[Coordinates]:
        """Get coordinates for all vials in the holder"""
        return [vial.coordinates for vial in self.vials]

    def validate_holder(self) -> bool:
        """Check if all vials are properly positioned according to definition"""
        ref_coords = self.vials[0].coordinates
        spacing = self.definition.spacing_y

        for i, vial in enumerate(self.vials[1:], 1):
            expected_y = ref_coords.y - (i * spacing)
            if abs(vial.coordinates.y - expected_y) > 0.1:  # 0.1mm tolerance
                return False
            if abs(vial.coordinates.x - ref_coords.x) > 0.1:
                return False
        return True

    def get_vials_by_type(self, category: str) -> List[Union[StockVial, WasteVial]]:
        """Get all vials of a specific type in the holder"""
        return [
            vial
            for i, vial in enumerate(self.vials)
            if self.definition.get_vial_type(i) == category
        ]

    @property
    def reference_coordinates(self) -> Coordinates:
        """Get the coordinates of the reference vial"""
        return self.vials[0].coordinates

    def __repr__(self):
        return f"VialHolder(id={self.holder_id}, type={self.definition.name}, num_vials={len(self.vials)})"
