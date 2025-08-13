"""
SQL Tools Tip Rack Models

This module contains the SQLAlchemy ORM models for tip racks and tips.
"""

from datetime import datetime as dt
from datetime import timezone
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Boolean

from .base import Base, DeckObjectBase, VesselBase, CoordinatesMixin, AuditMixin

class Tip(Base, CoordinatesMixin, AuditMixin):
    __tablename__ = "panda_tips"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rack_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tip_id: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "A1"
    tip_length: Mapped[float] = mapped_column(Float, default=0)
    pickup_height: Mapped[float] = mapped_column(Float, default=0)
    radius_mm: Mapped[float] = mapped_column(Float, default=0)
    capacity: Mapped[int] = mapped_column(Integer, default=300)
    volume: Mapped[float] = mapped_column(Float, default=0)
    dead_volume: Mapped[float] = mapped_column(Float, default=0)
    contamination: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String, default="default")

    __table_args__ = (
        UniqueConstraint("rack_id", "tip_id", name="uq_tip_slot"),
    )

class TipModel(VesselBase, Base):
    """TipHx table model"""

    __tablename__ = "panda_tip_hx"
    __mapper_args__ = {
        "concrete": True,
        "exclude_properties": [
            "volume_height", "top", "bottom", "height",
            "base_thickness", "contents",
        ],
    }
    rack_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tip_id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    status_date: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), nullable=False
    )
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), nullable=False
    )
    tip_length: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pickup_height: Mapped[float] = mapped_column(Float, default=0.0)
    @property
    def radius_mm(self) -> Optional[float]:
        return getattr(self, "radius", None)
    
    def __repr__(self):
        return (
            f"<TipHx(rack_id={self.rack_id}, tip_id={self.tip_id}, "
            f"experiment_id={self.experiment_id}, project_id={self.project_id}, "
            f"status={self.status}, status_date={self.status_date}, "
            f"coordinates={self.coordinates}, radius_mm={self.radius}, "
            f"capacity={self.capacity}, top={self.top}, bottom={self.bottom}, "
            f"pickup_height={self.pickup_height}, "
            f"updated={self.updated})>"
        )

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

class Racks(Base, DeckObjectBase):
    """Tip Racks table model

    Attributes:
        id (int): The tip rack ID.
        type_id (int): The tip rack type ID.
        current (bool): Is the tip rack the currently active tip rack on the deck.
        a1_x (float): The x-coordinate of well A1.
        a1_y (float): The y-coordinate of well A1.
        orientation (int): The orientation of the well plate.
        rows (str): The rows of the well plate.
        cols (int): The columns of the well plate.
        pickup_height (float): The height for pipette tip pickup.
    """

    __tablename__ = "panda_tipracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_tiprack_types.id")
    )
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    a1_x: Mapped[float] = mapped_column(Float)
    a1_y: Mapped[float] = mapped_column(Float)
    orientation: Mapped[int] = mapped_column(Integer, default=0)
    rows: Mapped[str] = mapped_column(String, default="ABCDEFGH")
    cols: Mapped[int] = mapped_column(Integer, default=12)
    pickup_height: Mapped[float] = mapped_column(Float)
    drop_coordinates: Mapped[dict] = mapped_column(
        JSON, nullable=True, default={"x": 0.0, "y": 0.0, "z": 0.0}
    )
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<Tipracks(id={self.id}, type_id={self.type_id}, current={self.current})>"


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
