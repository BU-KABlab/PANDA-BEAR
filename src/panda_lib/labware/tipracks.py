import logging
from typing import Optional, Tuple, Union

from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker

# from panda_lib.exceptions import OverDraftException, OverFillException

from panda_lib.hardware.gantry_interface import Coordinates
from panda_lib.labware.services import RackService, TipService
from panda_lib.types import TipKwargs
from panda_shared.db_setup import SessionLocal

from panda_lib.labware.schemas import (
    RackTypeModel,
    RackReadModel,
    RackWriteModel,
    TipReadModel,
    TipWriteModel,
)


logger = logging.getLogger("panda")


class RackKwargs(BaseModel, validate_assignment=True):
    """
    Model for Rack kwargs

    Attributes:
    -----------
    type_id: int
    a1_x: float
    a1_y: float
    orientation: int
    rows: str
    cols: int
    pickup_height: float
    coordinates: dict
    """

    name: str | None = None
    type_id: int | None = None
    a1_x: float = 0.0
    a1_y: float = 0.0
    orientation: int = 0
    rows: str = "ABCD"
    cols: int = 14
    pickup_height: float = 0.0
    coordinates: dict = {"x": 0.0, "y": 0.0, "z": 0.0}


class Rack:
    """Tip rack container."""

    def __init__(
        self,
        session_maker: sessionmaker = SessionLocal,
        type_id: Optional[int] = None,
        rack_id: Optional[int] = None,
        create_new: bool = False,
        **kwargs: RackKwargs,
    ):
        self.database_session = session_maker
        self.service = RackService(session_maker)
        self.tip_service = TipService(session_maker)
        self.rack_data: RackReadModel = None
        self.rack_type: RackTypeModel = None
        self.tips: dict[str, TipReadModel] = {}

        if create_new:
            if type_id is None and "type_id" not in kwargs:
                raise ValueError("Must provide a rack type_id to create a new rack.")
            self.create_new_rack(id=rack_id, type_id=type_id, **kwargs)
        else:
            if rack_id is None:
                active = self.service.get_active_rack()
                if not active:
                    raise ValueError(
                        "No rack_id provided and no active rack found in the database."
                    )
                rack_id = active.id
            self.load_rack(rack_id)

    def create_new_rack(self, **kwargs: RackKwargs):
        """Create a new rack and seed its tips."""

        active_rack = self.service.get_active_rack()
        if active_rack:
            kwargs.setdefault("a1_x", active_rack.a1_x)
            kwargs.setdefault("a1_y", active_rack.a1_y)
            kwargs.setdefault("orientation", active_rack.orientation)
            kwargs.setdefault("pickup_height", active_rack.pickup_height)
            kwargs.setdefault("coordinates", active_rack.coordinates)

        if "name" not in kwargs:
            kwargs["name"] = f"{kwargs.get('id', 'default')}"

        self.rack_type = self.service.get_rack_type(kwargs.get("type_id"))
        for key, value in self.rack_type.model_dump().items():
            if key == "id":
                continue
            if key not in kwargs:
                kwargs[key] = value

        new_rack = RackWriteModel(**kwargs)
        self.rack_data = RackWriteModel.model_validate(
            self.service.create_rack(new_rack)
        )

        self._create_tips_from_type()
        self.load_rack(self.rack_data.id)

    def load_rack(self, rack_id: int):
        """Load rack information and associated tips."""
        self.rack_data = self.service.get_rack(rack_id)
        self.rack_type = self.service.get_rack_type(self.rack_data.type_id)
        self.load_tips()

    def load_tips(self):
        """Load tips belonging to this rack using :class:`TipService`."""
        tip_ids = [tip.tip_id for tip in self.service.get_tips(self.rack_data.id)]
        self.tips = {
            tip_id: self.tip_service.get_tip(tip_id, self.rack_data.id)
            for tip_id in tip_ids
        }

    def save(self):
        """Persist current rack data to the database."""
        self.service.update_rack(self.rack_data.id, self.rack_data.model_dump())
        self.load_rack(self.rack_data.id)

    def _create_tips_from_type(self):
        """Populate tip entries for this rack based on its type."""
        with self.database_session() as session:
            self.service.seed_tips_for_rack(session, self.rack_data.id)

    def calculate_tip_coordinates(self, row: str, col: int) -> dict:
        """Calculate tip coordinates based on A1 position and orientation."""

        r_idx = self.rack_data.rows.index(row.upper())
        c_idx = col - 1
        a1_x = self.rack_data.a1_x
        a1_y = self.rack_data.a1_y
        x_spacing = self.rack_type.x_spacing
        y_spacing = self.rack_type.y_spacing
        o = self.rack_data.orientation % 360

        x = a1_x + r_idx * x_spacing
        y = a1_y + c_idx * y_spacing

        if o == 90:
            x, y = a1_x - (y - a1_y), a1_y + (x - a1_x)
        elif o == 180:
            x, y = a1_x - (x - a1_x), a1_y - (y - a1_y)
        elif o == 270:
            x, y = a1_x + (y - a1_y), a1_y - (x - a1_x)

        return {"x": x, "y": y, "z": self.rack_data.pickup_height}


class Tip:
    """
    Class to represent a tip in a tiprack

    Attributes:
    -----------
    tip_id: str
        The tip id
    rack_id: int
        The plate id
    session: sessionmaker
        The database session
    create_new: bool
        If True, create a new tip
    kwargs: TipKwargs
        Keyword arguments for making the tip
    tip_data: Optional[TipReadModel]
        The tip data

    Methods:
    --------
    create_new_tip(**kwargs: TipKwargs)
        Create a new tip
    load_tip()
        Load the tip
    save()
        Save the tip
    update_status(new_status: str)
        Update the status of the tip
    update_coordinates(new_coordinates: dict)
        Update the coordinates of the tip
    __repr__()
        Return a string representation of the tip

    """

    def __init__(
        self,
        tip_id: str,
        session_maker: sessionmaker = SessionLocal,
        create_new: bool = False,
        **kwargs: TipKwargs,
    ):
        self.tip_id = tip_id
        self.session_maker = session_maker
        self.service = TipService(session_maker=session_maker)
        self.tip_data: TipReadModel

        if create_new:
            self.create_new_tip(**kwargs)
        else:
            self.load_tip()

    @property
    def name(self):
        return self.tip_data.name

    @property
    def coordinates(self):
        return self.tip_data.coordinates

    @property
    def x(self):
        return self.tip_data.coordinates.get("x")

    @property
    def y(self):
        return self.tip_data.coordinates.get("y")

    @property
    def z(self):
        return self.tip_data.coordinates.get("z")

    @property
    def top(self):
        """The z-coordinate of the top of the tip in mm"""
        return self.tip_data.top

    @property
    def bottom(self):
        """The z-coordinate of the bottom of the tip in mm"""
        return self.tip_data.bottom

    @property
    def capacity(self):
        """The volume of the tip in microliters"""
        return self.tip_data.capacity

    @property
    def status(self):
        return self.tip_data.status

    @property
    def pickup_height(self) -> float:
        """Returns the height the pipette has to go to for tip pickup."""
        return getattr(self.tip_data, "pickup_height", None) or self.bottom

    @property
    def top_coordinates(self) -> Coordinates:
        """Returns the top coordinates of the tip."""
        return Coordinates(x=self.x, y=self.y, z=self.top)

    @property
    def bottom_coordinates(self) -> Coordinates:
        """Returns the bottom coordinates of the tip."""
        return Coordinates(x=self.x, y=self.y, z=self.bottom)

    @property
    def drop_x(self):
        return getattr(self.tip_data, "drop_x", None)

    @property
    def drop_y(self):
        return getattr(self.tip_data, "drop_y", None)

    @property
    def drop_z(self):
        return getattr(self.tip_data, "drop_z", None)

    @property
    def drop_coordinates(self) -> Coordinates:
        return Coordinates(**self.tip_data.drop_coordinates)

    @property
    def experiment_id(self):
        return self.tip_data.experiment_id

    def create_new_tip(self, **kwargs: TipKwargs):
        # Fetch rack type info
        if "type_id" in kwargs:
            rack_type = self.service.fetch_tip_type_characteristics(
                db_session=self.session_maker,
                rack_id=self.rack_id,
                type_id=kwargs.get("type_id"),
            )
        else:
            rack_type = self.service.fetch_tip_type_characteristics(
                db_session=self.session_maker, rack_id=self.rack_id
            )

        # Remove rack_type attributes from kwargs if they exist
        for key in ["capacity", "radius"]:
            kwargs.pop(key, None)

        # Fetch rack info so we can get drop coordinates
        rack = self.service.get_rack_for_tip(self.rack_id)
        drop_coords = getattr(rack, "drop_coordinates", None)
        if not drop_coords:
            # Default to rack coordinates but Z slightly above top
            drop_coords = {
                "x": rack.coordinates["x"],
                "y": rack.coordinates["y"],
                "z": rack.coordinates["z"] + rack.pickup_height + 20,
            }
        # Create tip entry
        kwargs.setdefault("pickup_height", rack.pickup_height)
        new_tip = TipWriteModel(
            tip_id=self.tip_id,
            rack_id=self.rack_id,
            capacity=rack_type.capacity_ul,
            drop_coordinates=drop_coords,
            **kwargs,
        )

        self.tip_data = TipWriteModel.model_validate(self.service.create_tip(new_tip))
        self.save()
        self.load_tip()

    def load_tip(self):
        """Load the tip data from the database"""
        self.tip_data: TipReadModel = self.service.get_tip(self.tip_id, self.rack_id)

    def save(self):
        """Save the tip data to the database"""
        self.service.update_tip(self.tip_id, self.rack_id, self.tip_data.model_dump())
        self.load_tip()

    def update_status(self, new_status: str):
        """Update the status of the tip"""
        self.tip_data.status = new_status
        self.save()

    def update_coordinates(self, new_coordinates: Union[dict, Coordinates]):
        """Update the coordinates of the tip and save to the database"""
        if isinstance(new_coordinates, Coordinates):
            new_coordinates = new_coordinates.to_dict()
        self.tip_data.coordinates = new_coordinates
        self.save()

    def get_xyz(self) -> Tuple[float, float, float]:
        """Get the x, y, z coordinates of the tip"""
        return (
            self.tip_data.coordinates["x"],
            self.tip_data.coordinates["y"],
            self.tip_data.coordinates["z"],
        )

    def __repr__(self):
        return f"<tip(tip_id={self.tip_id}, volume={self.tip_data.volume}, contents={self.tip_data.contents})>"
