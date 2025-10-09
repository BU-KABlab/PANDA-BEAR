from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import (
    Integer,
    String,
)

from .base import Base


class Protocols(Base):
    """Protocols table model"""

    __tablename__ = "panda_protocols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)
