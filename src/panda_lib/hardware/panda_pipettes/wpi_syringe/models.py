import json
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Column, ForeignKey
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.sql.sqltypes import (
    Float,
    Integer,
    String,
)
from sqlalchemy.types import TypeDecorator

Base = declarative_base()


class JSONEncodedDict(TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""

    impl = String

    def process_bind_param(self, value, dialect):
        if value is None:
            return "{}"
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        return json.loads(value)


def model_to_dict(model):
    """Convert a SQLAlchemy model to a dictionary."""
    return {c.key: getattr(model, c.key) for c in inspect(model).mapper.column_attrs}


class panda_units(Base):
    """
    Panda Units table model

    Attributes:
        id (int): The unit ID.
        version (float): The version of the unit.
        name (str): The name of the unit.
    """

    __tablename__ = "panda_units"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[float] = mapped_column(Float, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"<PandaUnit(id={self.id}, version={self.version}, name={self.name})>"


class Pipette(Base):
    """
    Pipette table model

    Attributes:
        id (int): The pipette ID.
        capacity_ul (float): The pipette capacity in microliters.
        capacity_ml (float): The pipette capacity in milliliters.
        volume_ul (float): The pipette volume in microliters.
        volume_ml (float): The pipette volume in milliliters.
        contents (str): The contents of the pipette.
        updated (datetime): The last time the pipette was updated.
        active (int): The status of the pipette. 0 = inactive, 1 = active.
        uses (int): The number of times the pipette has been used.
        panda_unit_id (int): The ID of the panda unit associated with the pipette.


    """

    __tablename__ = "panda_pipette"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capacity_ul: Mapped[float] = mapped_column(Float, nullable=False)
    capacity_ml: Mapped[float] = mapped_column(Float, nullable=False)
    volume_ul: Mapped[float] = mapped_column(Float, nullable=False)
    volume_ml: Mapped[float] = mapped_column(Float, nullable=False)
    contents: Mapped[dict] = mapped_column(JSONEncodedDict())
    updated: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    active: Mapped[int] = mapped_column(Integer)  # 0 = inactive, 1 = active
    uses: Mapped[int] = mapped_column(Integer, default=0)
    panda_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_units.id"), nullable=False
    )

    def __repr__(self):
        return f"<Pipette(id={self.id}, capacity_ul={self.capacity_ul}, capacity_ml={self.capacity_ml}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, contents={self.contents}, updated={self.updated})>"


class PipetteLog(Base):
    """PipetteLog table model"""

    __tablename__ = "panda_pipette_log"
    id = Column(Integer, primary_key=True)
    pipette_id = Column(Integer, ForeignKey("panda_pipette.id"))
    volume_ul = Column(Float, nullable=False)
    volume_ml = Column(Float, nullable=False)
    updated = Column(String, default=dt.now(timezone.utc))
    panda_unit_id = Column(Integer, ForeignKey("panda_units.id"), nullable=False)

    def __repr__(self):
        return f"<PipetteLog(id={self.id}, pipette_id={self.pipette_id}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, updated={self.updated})>"
