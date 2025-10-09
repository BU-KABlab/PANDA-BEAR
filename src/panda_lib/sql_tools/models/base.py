"""
SQL Tools Base Models

This module contains the base SQLAlchemy models and shared data types.
"""

import json
from datetime import datetime as dt
from datetime import timezone
from typing import Any, Dict, Optional
from sqlalchemy import String, Integer, Float, Text, UniqueConstraint
import sqlalchemy as sa
from sqlalchemy import Column, Computed, ForeignKey, Table, Text, event, select
from sqlalchemy.ext import compiler
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table
from sqlalchemy.sql.sqltypes import (
    JSON,
    Boolean,
    Float,
    Integer,
    String,
)
from sqlalchemy.types import TypeDecorator

# Create the base model class
Base = declarative_base()


class JSONEncodedDict(TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""

    impl = Text
    cache_ok = True

    def process_bind_param(
        self, value: Optional[Dict[str, Any]], dialect: Any
    ) -> Optional[str]:
        """Convert Python dict to JSON string for database storage."""
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(
        self, value: Optional[str], dialect: Any
    ) -> Optional[Dict[str, Any]]:
        """Convert JSON string from database to Python dict."""
        if value is None:
            return None
        return json.loads(value)


Base = declarative_base()

class DeckObjectBase:
    """Base class for DeckObject models

    Attributes:
        coordinates (dict): The object coordinates.
        base_thickness (float): The base thickness of the object.
        height (float): The height of the object.
        top (float): The top of the object.
        bottom (float): The bottom of the object.
        name (str): The name of the object.
    """

    coordinates: Mapped[dict] = mapped_column(JSON, default={"x": 0, "y": 0, "z": 0})
    base_thickness: Mapped[float] = mapped_column(Float, default=1.0)
    height: Mapped[float] = mapped_column(Float, default=6.0)
    top: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(json_extract(coordinates, '$.z') + base_thickness + height, 2)",
            persisted=True,
        ),
        nullable=True,
    )
    bottom: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(json_extract(coordinates, '$.z') + base_thickness, 2)",
            persisted=True,
        ),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String)


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


def model_to_dict(model):
    """Convert a SQLAlchemy model to a dictionary."""
    return {c.key: getattr(model, c.key) for c in inspect(model).mapper.column_attrs}


class MlPedotBestTestPoints(Base):
    """MlPedotBestTestPoints table model"""

    __tablename__ = "panda_ml_pedot_best_test_points"
    model_id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, unique=True)
    best_test_point_scalar = Column(String)
    best_test_point_original = Column(String)
    best_test_point = Column(String)
    v_dep = Column(Float(18, 8))
    t_dep = Column(Float(18, 8))
    edot_concentration = Column(Float(18, 8))
    predicted_response = Column(Float(18, 8))
    standard_deviation = Column(Float(18, 8))
    models_current_rmse = Column(Float(18, 8))

    def __repr__(self):
        return f"<MlPedotBestTestPoints(model_id={self.model_id}, experiment_id={self.experiment_id}, best_test_point_scalar={self.best_test_point_scalar}, best_test_point_original={self.best_test_point_original}, best_test_point={self.best_test_point}, v_dep={self.v_dep}, t_dep={self.t_dep}, edot_concentration={self.edot_concentration}, predicted_response={self.predicted_response}, standard_deviation={self.standard_deviation}, models_current_rmse={self.models_current_rmse})>"


class MlPedotTrainingData(Base):
    """MlPedotTrainingData table model"""

    __tablename__ = "panda_ml_pedot_training_data"
    id = Column(Integer, primary_key=True)
    delta_e = Column(Float(18, 8))
    voltage = Column(Float(18, 8))
    time = Column(Float(18, 8))
    bleach_cp = Column(Float(18, 8))
    concentration = Column(Float(18, 8))
    experiment_id = Column(Integer)

    def __repr__(self):
        return f"<MlPedotTrainingData(id={self.id}, delta_e={self.delta_e}, voltage={self.voltage}, time={self.time}, bleach_cp={self.bleach_cp}, concentration={self.concentration}, experiment_id={self.experiment_id})>"


class Projects(Base):
    """Projects table model"""

    __tablename__ = "panda_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String, nullable=True)
    added: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<Projects(id={self.id}, project_name={self.project_name}, added={self.added})>"


class SlackTickets(Base):
    """SlackTickets table model"""

    __tablename__ = "panda_slack_tickets"
    msg_id = Column(String, primary_key=True, nullable=False, unique=True)
    channel_id = Column(String, nullable=False)
    message = Column(String, nullable=False)
    response = Column(Integer)
    timestamp = Column(String)
    addressed_timestamp = Column(String)
    db_timestamp = Column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<SlackTickets(msg_id={self.msg_id}, channel_id={self.channel_id}, message={self.message}, response={self.response}, timestamp={self.timestamp}, addressed_timestamp={self.addressed_timestamp}, db_timestamp={self.db_timestamp})>"


class PandaUnits(Base):
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


class SystemStatus(Base):
    """SystemStatus table model"""

    __tablename__ = "panda_system_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String, nullable=False)
    comment = Column(String)
    status_time = Column(String, default=dt.now(timezone.utc))
    test_mode = Column(Boolean)
    panda_unit_id = Column(Integer, ForeignKey("panda_units.id"), nullable=False)

    def __repr__(self):
        return f"<SystemStatus(id={self.id}, status={self.status}, comment={self.comment}, status_time={self.status_time}, test_mode={self.test_mode})>"


class Users(Base):
    """Users table model"""

    __tablename__ = "panda_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first: Mapped[str] = mapped_column(String, nullable=False)
    last: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    full: Mapped[str] = mapped_column(
        String, Computed("first || ' ' || last", persisted=True)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc)
    )

    def __repr__(self):
        return (
            f"<Users(id={self.id}, first_name={self.first}, last_name={self.last}, "
            f"username={self.username}, password={self.password}, email={self.email}, "
            f"active={self.active}, full={self.full}, created_at={self.created_at}, "
            f"updated={self.updated})>"
        )

def generate_username(mapper, connection, target):
    """Generate a unique username by concatenating the first letter of the first name with the last name and an auto-incremented number."""
    if target.first and target.last:
        base_username = f"{target.first[0].lower()}{target.last.lower()}"
        existing_usernames = connection.scalars(
            select(Users.username).where(Users.username.like(f"{base_username}%"))
        )
        if existing_usernames:
            max_suffix = max(
                int(username[0].replace(base_username, "") or 0)
                for username in existing_usernames
            )
            target.username = f"{base_username}{max_suffix + 1}"
        else:
            target.username = base_username


# Attach the event listener to the Users model
event.listen(Users, "before_insert", generate_username)

# Junction table for the many-to-many relationship between users and projects
user_projects = Table(
    "panda_user_projects",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("panda_users.id"), primary_key=True),
    Column("project_id", Integer, ForeignKey("panda_projects.id"), primary_key=True),
    Column("current", Boolean, default=True),
    Column("timestamp", Integer, default=dt.now(timezone.utc)),
)


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view_exists(ddl, target, connection, **kw):
    return ddl.name in sa.inspect(connection).get_view_names()


def view_doesnt_exist(ddl, target, connection, **kw):
    return not view_exists(ddl, target, connection, **kw)


def view(name, metadata, selectable):
    t = table(name)

    t._columns._populate_separate_keys(
        col._make_proxy(t) for col in selectable.selected_columns
    )

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=view_doesnt_exist),
    )
    sa.event.listen(
        metadata, "before_drop", DropView(name).execute_if(callable_=view_exists)
    )
    return t


# NOTE: This is a view that is used to get the most recent vial status for each vial position


class PotentiostatReadout(Base):
    """PotentiostatReadout table model"""

    __tablename__ = "panda_potentiostat_readouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False)
    interface = Column(String, nullable=False)
    technique = Column(String, nullable=False)
    readout_values = Column(Text, nullable=False)
    experiment_id = Column(
        Integer, ForeignKey("panda_experiments.experiment_id"), nullable=False
    )

    # @staticmethod
    # def validate_interface(mapper, connection, target):
    #     """Validate if the technique is listed in the PotentiostatTechniques table and the interface is supported."""
    #     technique = connection.execute(
    #         f"SELECT * FROM panda_potentiostat_techniques WHERE technique = '{target.technique}'"
    #     ).fetchone()

    #     if not technique:
    #         raise ValueError(f"Technique '{target.technique}' is not listed in the PotentiostatTechniques table.")

    #     interface_column = f"gamry_{target.interface}"
    #     if not getattr(technique, interface_column, False):
    #         raise ValueError(f"Interface '{target.interface}' is not supported for technique '{target.technique}'.")


# Attach the event listener to the PotentiostatReadout model
# event.listen(PotentiostatReadout, 'before_insert', PotentiostatReadout.validate_interface)


class PotentiostatTechniques(Base):
    """PotentiostatTechniques table model"""

    __tablename__ = "panda_potentiostat_techniques"

    id = Column(Integer, primary_key=True)
    technique = Column(String, nullable=False)
    technique_description = Column(String, nullable=True)
    technique_params = Column(JSON, nullable=True)
    gamry_1010T = Column(Boolean, nullable=False)
    gamry_1010B = Column(Boolean, nullable=False)
    gamry_1010E = Column(Boolean, nullable=False)
