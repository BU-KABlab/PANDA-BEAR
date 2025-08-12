from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import (
    BigInteger,
    Boolean,
    Float,
    Integer,
    String,
)

from .base import Base


class Experiments(Base):
    """Experiments table model"""

    __tablename__ = "panda_experiments"
    experiment_id = Column(BigInteger, primary_key=True)
    project_id = Column(Integer)
    project_campaign_id = Column(Integer)
    well_type = Column(Integer)
    protocol_id = Column(String)
    analysis_id = Column(Integer)
    priority = Column(Integer, default=0)
    filename = Column(String, default=None)
    needs_analysis = Column(Boolean, default=False)
    panda_version = Column(Float, default=1.0)
    panda_unit_id = Column(Integer, ForeignKey("panda_units.id"), nullable=True)
    created = Column(String, default=dt.now(timezone.utc))
    updated = Column(String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc))

    results: Mapped[list["ExperimentResults"]] = relationship(
        "ExperimentResults", backref="experiment"
    )
    parameters: Mapped[list["ExperimentParameters"]] = relationship(
        "ExperimentParameters", backref="experiment"
    )

    def __repr__(self):
        return (
            f"<Experiments(experiment_id={self.experiment_id}, project_id={self.project_id}, "
            f"project_campaign_id={self.project_campaign_id}, well_type={self.well_type}, "
            f"protocol_id={self.protocol_id}, priority={self.priority}, "
            f"filename={self.filename}, needs_analysis={self.needs_analysis}, "
            f"analysis_id={self.analysis_id}, panda_version={self.panda_version}, "
            f"panda_unit_id={self.panda_unit_id}, created={self.created}, updated={self.updated})>"
        )

class ExperimentStatusView:
    """ExperimentStatus view model"""

    __tablename__ = "panda_experiment_status"
    experiment_id = Column(Integer, primary_key=True)
    status = Column(String)

    def __repr__(self):
        return f"<ExperimentStatus(experiment_id={self.experiment_id}, status={self.status})>"


class ExperimentResults(Base):
    """ExperimentResults table model"""

    __tablename__ = "panda_experiment_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_experiments.experiment_id")
    )
    result_type: Mapped[str] = mapped_column(String)
    result_value: Mapped[str] = mapped_column(String)
    context: Mapped[str] = mapped_column(String)
    created: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc)
    )

    def __repr__(self):
        return f"<ExperimentResults(id={self.id}, experiment_id={self.experiment_id}, result_type={self.result_type}, result_value={self.result_value}, created={self.created}, updated={self.updated}, context={self.context})>"


class ExperimentParameters(Base):
    """ExperimentParameters table model"""

    __tablename__ = "panda_experiment_parameters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("panda_experiments.experiment_id")
    )
    parameter_name: Mapped[str] = mapped_column(String, nullable=True)
    parameter_value: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc)
    )

    def __repr__(self):
        return f"<ExperimentParameters(id={self.id}, experiment_id={self.experiment_id}, parameter_name={self.parameter_name}, parameter_value={self.parameter_value}, created={self.created}, updated={self.updated})>"
