from datetime import datetime as dt
from datetime import timezone

import sqlalchemy as sa
from sqlalchemy import Computed, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import (
    JSON,
    Boolean,
    Float,
    Integer,
    String,
)

from .base import Base, DeckObjectBase, JSONEncodedDict, view


class VesselBase(DeckObjectBase):
    radius: Mapped[int] = mapped_column(Integer, default=14)
    volume: Mapped[float] = mapped_column(Float, default=20000)
    capacity: Mapped[int] = mapped_column(Integer, default=20000)
    contamination: Mapped[int] = mapped_column(Integer, default=0)
    dead_volume: Mapped[int] = mapped_column(Integer, default=1000)
    volume_height: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(json_extract(coordinates, '$.z') + base_thickness + ((volume) / (3.1459 * radius * radius)), 2)",
            persisted=True,
        ),
        nullable=True,
    )
    contents: Mapped[dict] = mapped_column(JSON, default={})
    bottom: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(json_extract(coordinates, '$.z') + base_thickness + ((dead_volume) / (3.1459 * radius * radius)), 2)",
            persisted=True,
        ),
        nullable=True,
    )


class VialsBase(VesselBase):
    """Base class for Vials and VialStatus models"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position: Mapped[str] = mapped_column(String)
    category: Mapped[int] = mapped_column(Integer)
    viscosity_cp: Mapped[float] = mapped_column(Float)
    concentration: Mapped[float] = mapped_column(Float)
    density: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, coordinates={self.coordinates}, updated={self.updated})>"


class Vials(Base):
    """Vials table model"""

    __tablename__ = "panda_vials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    contents: Mapped[dict] = mapped_column(JSONEncodedDict, nullable=False, default={})
    viscosity_cp: Mapped[float] = mapped_column(Float, nullable=False)
    concentration: Mapped[float] = mapped_column(Float, nullable=False)
    density: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=57.0)
    radius: Mapped[float] = mapped_column(Float, nullable=False, default=14.0)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=20000.0)
    capacity: Mapped[float] = mapped_column(Float, nullable=False, default=20000.0)
    contamination: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coordinates: Mapped[dict] = mapped_column(
        JSONEncodedDict, nullable=False, default={"x": 0, "y": 0, "z": 0}
    )
    base_thickness: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    dead_volume: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated: Mapped[str] = mapped_column(
        String, nullable=False, default=dt.now(timezone.utc)
    )

    # Generated columns
    volume_height: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (volume / (3.1459 * radius * radius)), 2)",
            persisted=True,
        ),
        nullable=True,
    )
    top: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + height, 2)",
            persisted=True,
        ),
        nullable=True,
    )
    bottom: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (dead_volume / (3.1459 * radius * radius)), 2)",
            persisted=True,
        ),
        nullable=True,
    )

    # Relationships
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<Vials(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, coordinates={self.coordinates}, updated={self.updated})>"

    @property
    def x(self):
        return self.coordinates.get("x", 0)

    @property
    def y(self):
        return self.coordinates.get("y", 0)

    @property
    def z(self):
        return self.coordinates.get("z", 0)


_subquery = sa.select(
    sa.func.row_number()
    .over(partition_by=Vials.position, order_by=Vials.updated.desc())
    .label("rn"),
    Vials,
).alias("RankedVials")

_vial_status_view = view(
    "panda_vial_status",
    Base.metadata,
    sa.select(
        _subquery.c.id.label("id"),
        _subquery.c.position.label("position"),
        _subquery.c.category.label("category"),
        _subquery.c.viscosity_cp.label("viscosity_cp"),
        _subquery.c.concentration.label("concentration"),
        _subquery.c.density.label("density"),
        _subquery.c.active.label("active"),
        _subquery.c.updated.label("updated"),
        _subquery.c.coordinates.label("coordinates"),
        _subquery.c.base_thickness.label("base_thickness"),
        _subquery.c.height.label("height"),
        _subquery.c.top.label("top"),
        _subquery.c.bottom.label("bottom"),
        _subquery.c.name.label("name"),
        _subquery.c.radius.label("radius"),
        _subquery.c.volume.label("volume"),
        _subquery.c.capacity.label("capacity"),
        _subquery.c.contamination.label("contamination"),
        _subquery.c.dead_volume.label("dead_volume"),
        _subquery.c.volume_height.label("volume_height"),
        _subquery.c.contents.label("contents"),
        _subquery.c.panda_unit_id.label("panda_unit_id"),
    ).where(_subquery.c.rn == 1),
)


class VialStatus(Base):
    """VialStatus view model"""

    __table__ = _vial_status_view

    def __repr__(self):
        return f"<VialStatus(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, coordinates={self.coordinates}, updated={self.updated})>"

    @property
    def x(self):
        return self.coordinates.get("x", 0)

    @property
    def y(self):
        return self.coordinates.get("y", 0)

    @property
    def z(self):
        return self.coordinates.get("z", 0)
