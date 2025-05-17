from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import (
    Integer,
    String,
)

from .base import Base


class ExperimentGenerators(Base):
    """ExperimentGenerators table model"""

    __tablename__ = "panda_generators"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    protocol_id = Column(Integer)
    name = Column(String)
    filepath = Column(String)

    def __repr__(self):
        return f"<ExperimentGenerators(id={self.id}, project_id={self.project_id}, protocol_id={self.protocol_id}, name={self.name}, filepath={self.filepath})>"
