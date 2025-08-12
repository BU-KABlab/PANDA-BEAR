import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

# from panda_lib.exceptions import OverDraftException, OverFillException

from panda_lib.hardware.gantry_interface import Coordinates
from panda_lib.labware.services import RackService, TipService
from panda_lib.sql_tools import (
    ExperimentParameters,
    ExperimentResults,
    Experiments,
    TipModel,
    Racks,
)
from panda_lib.types import TipKwargs
from panda_shared.config.config_tools import read_config_value
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
        """Returns the height of the pipette has to go to for tip pickup."""
        return self.bottom

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
                db_session=self.session_maker,
                rack_id=self.rack_id
            )

        # Remove rack_type attributes from kwargs if they exist
        for key in ["capacity", "radius_mm"]:
            kwargs.pop(key, None)

        # Fetch rack info so we can get drop coordinates
        rack = self.service.get_rack_for_tip(self.rack_id)
        drop_coords = getattr(rack, "drop_coordinates", None)
        if not drop_coords:
            # Default to rack coordinates but Z slightly above top
            drop_coords = {
                "x": rack.coordinates["x"],
                "y": rack.coordinates["y"],
                "z": rack.coordinates["z"] + rack.pickup_height + 20
            }

        # Create tip entry
        new_tip = TipWriteModel(
            tip_id=self.tip_id,
            rack_id=self.rack_id,
            capacity=rack_type.capacity_ul,
            drop_coordinates=drop_coords,
            **kwargs,
        )

        self.tip_data = TipWriteModel.model_validate(
            self.service.create_tip(new_tip)
        )
        self.save()
        self.load_tip()


    def load_tip(self):
        """Load the tip data from the database"""
        self.tip_data: TipReadModel = self.service.get_tip(
            self.tip_id, self.rack_id
        )

    def save(self):
        """Save the tip data to the database"""
        self.service.update_tip(
            self.tip_id, self.rack_id, self.tip_data.model_dump()
        )
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

