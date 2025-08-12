from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class DeckObjectModel(BaseModel):
    name: str
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    base_thickness: float = 1.0
    height: float = 6.0
    top: Optional[float] = None
    bottom: Optional[float] = None
    # @property
    # def top(self) -> float:
    #     return self.coordinates["z"] + self.base_thickness + self.height

    # @property
    # def bottom(self) -> float:
    #     return self.coordinates["z"] + self.base_thickness

    model_config = ConfigDict(from_attributes=True)

    @property
    def x(self) -> float:
        return self.coordinates["x"]

    @property
    def y(self) -> float:
        return self.coordinates["y"]

    @property
    def z(self) -> float:
        return self.coordinates["z"]

    @x.setter
    def x(self, value: float):
        self.coordinates["x"] = value

    @y.setter
    def y(self, value: float):
        self.coordinates["y"] = value

    @z.setter
    def z(self, value: float):
        self.coordinates["z"] = value


class VesselModel(DeckObjectModel):
    radius: float = 14.0
    volume: float = 20000.0
    capacity: float = 20000.0
    contamination: int = 0
    dead_volume: float = 1000.0
    contents: Dict[str, float] = Field(default_factory=dict)
    volume_height: float = 0.0


class VialWriteModel(BaseModel):
    position: str
    category: int  # 0 for stock, 1 for waste
    height: float = 57.0
    radius: float = 13.5
    volume: float = 20000.0  # in microliters
    capacity: float = 20000.0
    contamination: int = 0
    dead_volume: float = 1000.0
    contents: Dict[str, float] = Field(default_factory=dict)
    viscosity_cp: float = 0.0
    concentration: float = 0.0
    density: float = 1.0
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    name: str = "default"
    base_thickness: float = 1.0
    panda_unit_id: int = 1
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_kwargs(cls, **kwargs):
        return cls(**kwargs)


class VialReadModel(VesselModel):
    id: int
    position: str
    category: int
    viscosity_cp: float = 0.0
    concentration: float = 0.0
    density: float = 1.0
    active: int = 1
    panda_unit_id: int = 1
    updated: str

    model_config = ConfigDict(from_attributes=True)


class WellWriteModel(BaseModel):
    plate_id: int
    well_id: str
    experiment_id: int = 0
    project_id: int = 0
    status: str = "new"
    contents: Dict[str, float] = Field(default_factory=dict)
    volume: float = 0.0
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    base_thickness: float = 1.0
    height: float = 6.0
    radius: float = 3.0
    capacity: float = 20000.0
    contamination: int = 0
    dead_volume: float = 0.0
    name: str = "default"

    model_config = ConfigDict(from_attributes=True)


class WellReadModel(VesselModel):
    well_id: str
    plate_id: int
    experiment_id: Optional[int]
    project_id: Optional[int]
    status: str = "new"

    model_config = ConfigDict(from_attributes=True)


class PlateTypeModel(BaseModel):
    id: int
    substrate: str
    gasket: str
    count: int
    rows: str
    cols: int
    shape: str
    radius_mm: float
    y_spacing: float
    x_spacing: float
    gasket_length_mm: float
    gasket_width_mm: float
    gasket_height_mm: float
    x_offset: float
    y_offset: float
    max_liquid_height_mm: float
    capacity_ul: float
    base_thickness: float

    model_config = ConfigDict(from_attributes=True)


class WellplateReadModel(DeckObjectModel):
    id: int  # is allowed to be None, the db will autoincrement
    type_id: int
    current: bool
    a1_x: float
    a1_y: float
    orientation: int
    rows: str
    cols: int
    echem_height: float  # height of echem cell placement in mm
    image_height: float  # height of the image in mm
    panda_unit_id: int
    # TODO Add substrate and well count...probably inherit the PlateTypeModel instead or in addition to the DeckObjectModel
    model_config = ConfigDict(from_attributes=True)


class WellplateWriteModel(BaseModel):
    id: Optional[int] = None  # is allowed to be None, the db will autoincrement
    type_id: int
    current: bool = False
    a1_x: float = 0.0
    a1_y: float = 0.0
    orientation: int = 0
    rows: str = "ABCDEFGH"
    cols: int = 12
    echem_height: float = 0.0  # height of echem cell placement in mm
    image_height: float = 0.0  # height of the image in mm
    height: float = 6.0
    name: Optional[str] = f"{id}" if id is not None else None
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    base_thickness: float = 1.0
    panda_unit_id: int = 99

    model_config = ConfigDict(from_attributes=True)


class TipWriteModel(BaseModel):
    rack_id: int
    tip_id: str
    experiment_id: int = 0
    project_id: int = 0
    status: str = "new"
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    drop_coordinates: Dict[str, float] = Field(   
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    capacity: float = 200.0
    name: str = "default"
    type: int  # solid handling or liquid handling
    radius_mm: float  # radius of bead for solid handling

    model_config = ConfigDict(from_attributes=True)



class TipReadModel(VesselModel):
    tip_id: str
    rack_id: int
    experiment_id: Optional[int]
    project_id: Optional[int]
    status: str = "new"
    drop_coordinates: Dict[str, float] = Field(   
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )

    model_config = ConfigDict(from_attributes=True)



class RackTypeModel(BaseModel):
    id: int
    count: int
    rows: str
    cols: int
    shape: str
    radius_mm: float
    y_spacing: float
    x_spacing: float
    rack_length_mm: float
    rack_width_mm: float
    rack_height_mm: float
    x_offset: float
    y_offset: float

    model_config = ConfigDict(from_attributes=True)


class RackReadModel(DeckObjectModel):
    id: int  # is allowed to be None, the db will autoincrement
    type_id: int
    current: bool
    a1_x: float
    a1_y: float
    orientation: int
    rows: str
    cols: int
    pickup_height: float  # height of pipette to pick up tips
    drop_coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )

    panda_unit_id: int
    
    model_config = ConfigDict(from_attributes=True)


class RackWriteModel(BaseModel):
    id: Optional[int] = None  # is allowed to be None, the db will autoincrement
    type_id: int
    current: bool = False
    a1_x: float = 0.0
    a1_y: float = 0.0
    orientation: int = 0
    rows: str = "ABCD"
    cols: int = 14
    pickup_height: float = 0.0  # height of pipette to pick up tips
    name: Optional[str] = f"{id}" if id is not None else None
    coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    drop_coordinates: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    panda_unit_id: int = 2

    model_config = ConfigDict(from_attributes=True)
