"""
SQL Tools Wellplate Models

This module contains the SQLAlchemy ORM models for wellplates and wells.
"""

from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Boolean

from .base import Base, DeckObjectBase, VesselBase


class WellModel(VesselBase, Base):
    """WellHx table model"""

    __tablename__ = "panda_well_hx"
    plate_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    dead_volume: Mapped[int] = mapped_column(Integer, default=100)
    status_date: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), nullable=False
    )
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f"<WellHx(plate_id={self.plate_id}, well_id={self.well_id}, experiment_id={self.experiment_id}, project_id={self.project_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, volume={self.volume}, coordinates={self.coordinates}, base_thickness={self.base_thickness}, height={self.height}, radius={self.radius}, capacity={self.capacity}, top={self.top}, bottom={self.bottom}, updated={self.updated})>"


class PlateTypes(Base):
    """PlateTypes table model"""

    __tablename__ = "panda_wellplate_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    substrate: Mapped[str] = mapped_column(String)
    gasket: Mapped[str] = mapped_column(String)
    count: Mapped[int] = mapped_column(Integer)
    rows: Mapped[str] = mapped_column(String)
    cols: Mapped[int] = mapped_column(Integer)
    shape: Mapped[str] = mapped_column(String)
    radius_mm: Mapped[float] = mapped_column(Float)
    y_spacing: Mapped[float] = mapped_column(Float)
    x_spacing: Mapped[float] = mapped_column(Float)
    gasket_length_mm: Mapped[float] = mapped_column(Float)
    gasket_width_mm: Mapped[float] = mapped_column(Float)
    gasket_height_mm: Mapped[float] = mapped_column(Float)
    x_offset: Mapped[float] = mapped_column(Float)
    y_offset: Mapped[float] = mapped_column(Float)
    max_liquid_height_mm: Mapped[float] = mapped_column(Float)
    capacity_ul: Mapped[float] = mapped_column(Float)
    base_thickness: Mapped[float] = mapped_column(Float, default=1.0)

    def __repr__(self):
        return f"<PlateTypes(id={self.id}, substrate={self.substrate}, gasket={self.gasket}, count={self.count}, shape={self.shape}, radius_mm={self.radius_mm}, offset_mm={self.y_spacing}, height_mm={self.gasket_height_mm}, max_liquid_height_mm={self.max_liquid_height_mm}, capacity_ul={self.capacity_ul})>"


class Wellplates(Base, DeckObjectBase):
    """Wellplates table model

    Attributes:
        id (int): The well plate ID.
        type_id (int): The well plate type ID.
        current (bool): Is the wellplate the currently active wellplate on the deck.
        a1_x (float): The x-coordinate of well A1.
        a1_y (float): The y-coordinate of well A1.
        orientation (int): The orientation of the well plate.
        rows (str): The rows of the well plate.
        cols (int): The columns of the well plate.
        echem_height (float): The height of the electrochemical cell.
        image_height (float): The height of the image.
        coordinates (dict): The object coordinates.
        base_thickness (float): The base thickness of the object.
        height (float): The height of the object.
        top (float): The top of the object.
        bottom (float): The bottom of the object.
        name (str): The name of the object.

    """

    __tablename__ = "panda_wellplates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_wellplate_types.id")
    )
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    a1_x: Mapped[float] = mapped_column(Float)
    a1_y: Mapped[float] = mapped_column(Float)
    orientation: Mapped[int] = mapped_column(Integer, default=0)
    rows: Mapped[str] = mapped_column(String, default="ABCDEFGH")
    cols: Mapped[int] = mapped_column(Integer, default=12)
    echem_height: Mapped[float] = mapped_column(Float)
    image_height: Mapped[float] = mapped_column(Float)
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<Wellplates(id={self.id}, type_id={self.type_id}, current={self.current})>"


class WellStatus:
    """WellStatus view model"""

    __tablename__ = "panda_well_status"
    plate_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_number: Mapped[int] = mapped_column(Integer)
    well_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String)
    status_date: Mapped[str] = mapped_column(String)
    contents: Mapped[dict] = mapped_column(JSON)
    experiment_id: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[int] = mapped_column(Integer)
    volume: Mapped[float] = mapped_column(Float)
    coordinates: Mapped[dict] = mapped_column(JSON)
    capacity: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<WellStatus(plate_id={self.plate_id}, type_number={self.type_number}, well_id={self.well_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, experiment_id={self.experiment_id}, project_id={self.project_id}, volume={self.volume}, coordinates={self.coordinates}, capacity={self.capacity}, height={self.height})>"


class Queue:
    """Queue view model"""

    __tablename__ = "panda_queue"
    experiment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer)
    project_campaign_id: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer)
    process_type: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    well_type: Mapped[str] = mapped_column(String, name="well type")
    well_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    status_date: Mapped[str] = mapped_column(String)
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<Queue(experiment_id={self.experiment_id}, project_id={self.project_id}, priority={self.priority}, process_type={self.process_type}, filename={self.filename}, well_type={self.well_type}, well_id={self.well_id}, status={self.status}, status_date={self.status_date})>"
