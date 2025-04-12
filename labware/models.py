"""
Base models for labware definitions in the PANDA system.
Contains all Pydantic models used for validating labware definitions.
"""

from typing import Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


class WellDefinition(BaseModel):
    """Pydantic model for well definition."""

    depth: float
    totalLiquidVolume: Optional[float] = None
    shape: str
    diameter: float
    x: float
    y: float
    z: float

    class Config:
        extra = "allow"


class Brand(BaseModel):
    """Pydantic model for labware brand information."""

    brand: str
    brandId: List[str]


class Dimensions(BaseModel):
    """Pydantic model for labware dimensions."""

    xDimension: float
    yDimension: float
    zDimension: float


class Metadata(BaseModel):
    """Pydantic model for labware metadata."""

    displayName: str
    displayCategory: str
    displayVolumeUnits: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class GroupMetadata(BaseModel):
    """Pydantic model for labware group metadata."""

    wellBottomShape: str = "flat"

    class Config:
        extra = "allow"


class Group(BaseModel):
    """Pydantic model for labware well groups."""

    metadata: GroupMetadata
    wells: List[str]


class Parameters(BaseModel):
    """Pydantic model for labware parameters."""

    loadName: str
    orientation: int = 0
    quirks: List[str] = Field(default_factory=list)
    isTiprack: bool = False
    isMagneticModuleCompatible: bool = False

    class Config:
        extra = "allow"


class Offset(BaseModel):
    """Pydantic model for labware corner offset."""

    x: float = 0
    y: float = 0
    z: float = 0


class LabwareDefinition(BaseModel):
    """Pydantic model for labware definition."""

    ordering: List[List[str]]
    brand: Brand
    metadata: Metadata
    dimensions: Dimensions
    wells: Dict[str, WellDefinition]
    groups: List[Group] = Field(default_factory=list)
    parameters: Parameters
    namespace: str
    version: int
    schemaVersion: int
    cornerOffsetFromSlot: Offset

    @field_validator("ordering")
    @classmethod
    def validate_ordering(cls, ordering):
        """Validate that ordering is correctly structured."""
        if not ordering:
            raise ValueError("Ordering cannot be empty")

        # Check that each row has the same number of elements
        row_lengths = [len(row) for row in ordering]
        if len(set(row_lengths)) > 1:
            raise ValueError(
                "All rows in ordering must have the same number of elements"
            )

        return ordering

    @model_validator(mode="after")
    def validate_wells_in_ordering(self) -> "LabwareDefinition":
        """Validate that all wells in ordering exist in wells."""
        # Extract all well IDs from ordering
        well_ids = [well for row in self.ordering for well in row if well]

        # Check that all well IDs in ordering exist in wells
        missing_wells = [well_id for well_id in well_ids if well_id not in self.wells]
        if missing_wells:
            raise ValueError(
                f"Wells in ordering not found in wells definition: {missing_wells}"
            )

        return self

    class Config:
        extra = "allow"
