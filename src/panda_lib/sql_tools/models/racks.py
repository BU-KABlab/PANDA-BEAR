"""
SQL Tools Tip Rack Models

This module contains the SQLAlchemy ORM models for tip racks and tips.
"""
from __future__ import annotations
from datetime import datetime as dt
from datetime import timezone
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Boolean

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, Float, String, Text, ForeignKey, UniqueConstraint

from .base import Base

class Base(DeclarativeBase):
    pass


class RackTypes(Base):
    """RackTypes table model"""

    __tablename__ = "panda_tiprack_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    rows: Mapped[str] = mapped_column(String)
    cols: Mapped[int] = mapped_column(Integer)
    shape: Mapped[str] = mapped_column(String)
    radius_mm: Mapped[float] = mapped_column(Float)
    y_spacing: Mapped[float] = mapped_column(Float)
    x_spacing: Mapped[float] = mapped_column(Float)
    rack_length_mm: Mapped[float] = mapped_column(Float)
    rack_width_mm: Mapped[float] = mapped_column(Float)
    rack_height_mm: Mapped[float] = mapped_column(Float)
    x_offset: Mapped[float] = mapped_column(Float)
    y_offset: Mapped[float] = mapped_column(Float)
    
    def __repr__(self):
        return (
            f"<RackTypes(id={self.id}, count={self.count}, rows={self.rows}, cols={self.cols}, "
            f"shape={self.shape}, radius_mm={self.radius_mm}, "
            f"x_spacing={self.x_spacing}, y_spacing={self.y_spacing}, "
            f"rack_length_mm={self.rack_length_mm}, rack_width_mm={self.rack_width_mm}, "
            f"rack_height_mm={self.rack_height_mm}, "
            f"x_offset={self.x_offset}, y_offset={self.y_offset})>"
        )

class Racks(Base):
    __tablename__ = "panda_tipracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("panda_tiprack_types.id"), nullable=False)

    # A1 origin on your stage in mm
    a1_x: Mapped[float] = mapped_column(Float, nullable=False)
    a1_y: Mapped[float] = mapped_column(Float, nullable=False)

    # Orientation of the rack relative to A1-as-origin.
    # Supported below: "standard", "rot180", "mirror_x", "mirror_y"
    orientation: Mapped[str] = mapped_column(String, default="standard")

    pickup_height: Mapped[float] = mapped_column(Float, default=0.0)
    panda_unit_id: Mapped[int] = mapped_column(Integer, default=0)
    drop_coordinates: Mapped[str | None] = mapped_column(Text, default=None)

    type: Mapped[RackTypes] = relationship(RackTypes)
    tips: Mapped[list[TipModel]] = relationship(back_populates="rack", cascade="all, delete-orphan")


    def __repr__(self):
        return (
            f"<Racks(id={self.id}, type_id={self.type_id}, a1_x={self.a1_x}, a1_y={self.a1_y}, "
            f"orientation={self.orientation}, pickup_height={self.pickup_height}, "
            f"panda_unit_id={self.panda_unit_id}, drop_coordinates={self.drop_coordinates})>"
        )
    

class TipModel(Base):
    """TipHx table model"""

    __tablename__ = "panda_tip_hx"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rack_id: Mapped[int] = mapped_column(ForeignKey("panda_tipracks.id"), nullable=False, index=True)
    tip_id: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "A1"

    # Status bookkeeping
    status: Mapped[str] = mapped_column(String, default="available")  # available, in_use, used, failed
    status_date: Mapped[str] = mapped_column(String, default="")
    updated: Mapped[str] = mapped_column(String, default="")

    # Geometry and capacity
    tip_length: Mapped[float] = mapped_column(Float, default=0.0)
    pickup_height: Mapped[float] = mapped_column(Float, default=0.0)
    radius_mm: Mapped[float] = mapped_column(Float, default=0.0)
    capacity: Mapped[int] = mapped_column(Integer, default=300)
    contamination: Mapped[int] = mapped_column(Integer, default=0)

    # Optional cached JSON blobs if you want them
    coordinates: Mapped[str | None] = mapped_column(Text, default=None)
    drop_coordinates: Mapped[str | None] = mapped_column(Text, default=None)

    name: Mapped[str] = mapped_column(String, default="default")

    rack: Mapped[Racks] = relationship(Racks, back_populates="tips")

    __table_args__ = (
        UniqueConstraint("rack_id", "tip_id", name="uq_tip_slot"),
    )

    def __repr__(self):
        return(
            f"<TipHx(rack_id={self.rack_id}, tip_id={self.tip_id}, "
            f"experiment_id={self.experiment_id}, project_id={self.project_id}, "
            f"status={self.status}, status_date={self.status_date}, "
            f"coordinates={self.coordinates}, radius_mm={self.radius_mm}, "
            f"capacity={self.capacity}, top={self.top}, bottom={self.bottom}, "
            f"pickup_height={self.pickup_height}, "
            f"updated={self.updated})>"
        )
    
class TipStatus:
    """TipStatus view model"""

    __tablename__ = "panda_tip_status"
    rack_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_number: Mapped[int] = mapped_column(Integer)
    tip_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String)
    status_date: Mapped[str] = mapped_column(String)
    experiment_id: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[int] = mapped_column(Integer)
    coordinates: Mapped[dict] = mapped_column(JSON)
    capacity: Mapped[float] = mapped_column(Float)
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<TipStatus(rack_id={self.rack_id}, type_number={self.type_number}, tip_id={self.tip_id}, status={self.status}, status_date={self.status_date}, experiment_id={self.experiment_id}, project_id={self.project_id}, coordinates={self.coordinates}, capacity={self.capacity})>"
