"""
SQLAlchemy models for the PANDA database
"""

# pylint: disable=too-few-public-methods, line-too-long
import json
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Column, Computed, ForeignKey, Table, Text, event, text
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.sql.sqltypes import (
    JSON,
    BigInteger,
    Boolean,
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


class Experiments(Base):
    """Experiments table model"""

    __tablename__ = "panda_experiments"
    experiment_id = Column(BigInteger, primary_key=True)
    project_id = Column(Integer)
    project_campaign_id = Column(Integer)
    well_type = Column(Integer)
    protocol_id = Column(Integer)
    analysis_id = Column(Integer)
    pin = Column(String)
    experiment_type = Column(Integer)
    jira_issue_key = Column(String)
    priority = Column(Integer, default=0)
    process_type = Column(Integer, default=0)
    filename = Column(String, default=None)
    needs_analysis = Column(Boolean, default=False)
    created = Column(String)
    updated = Column(String, default=dt.now(timezone.utc))

    results: Mapped[list["ExperimentResults"]] = relationship(
        "ExperimentResults", backref="experiment"
    )
    parameters: Mapped[list["ExperimentParameters"]] = relationship(
        "ExperimentParameters", backref="experiment"
    )

    def __repr__(self):
        return f"<Experiments(experiment_id={self.experiment_id}, project_id={self.project_id}, project_campaign_id={self.project_campaign_id}, well_type={self.well_type}, protocol_id={self.protocol_id}, pin={self.pin}, experiment_type={self.experiment_type}, jira_issue_key={self.jira_issue_key}, priority={self.priority}, process_type={self.process_type}, filename={self.filename}, created={self.created}, updated={self.updated})>"

    # @classmethod
    # def get_by_id(cls, session, experiment_id: int) -> Optional["Experiments"]:
    #     return session.query(cls).filter(cls.experiment_id == experiment_id).first()


class ExperimentStatusView(Base):
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
    parameter_name: Mapped[str] = mapped_column(String)
    parameter_value: Mapped[str] = mapped_column(String)
    created: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc)
    )

    def __repr__(self):
        return f"<ExperimentParameters(id={self.id}, experiment_id={self.experiment_id}, parameter_name={self.parameter_name}, parameter_value={self.parameter_value}, created={self.created}, updated={self.updated})>"


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

    def __repr__(self):
        return f"<PipetteLog(id={self.id}, pipette_id={self.pipette_id}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, updated={self.updated})>"


class Projects(Base):
    """Projects table model"""

    __tablename__ = "panda_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String)
    added: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<Projects(id={self.id}, project_name={self.project_name}, added={self.added})>"


class Protocols(Base):
    """Protocols table model"""

    __tablename__ = "panda_protocols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)


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


class SystemStatus(Base):
    """SystemStatus table model"""

    __tablename__ = "panda_system_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String, nullable=False)
    comment = Column(String)
    status_time = Column(String, default=dt.now(timezone.utc))
    test_mode = Column(Boolean)

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
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))
    updated: Mapped[str] = mapped_column(
        String, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc)
    )

    def __repr__(self):
        return f"<Users(id={self.id}, first_name={self.first}, last_name={self.last}, username={self.username}, password={self.password}, email={self.email}, created={self.created}, updated={self.updated})>"


def generate_username(mapper, connection, target):
    """Generate a unique username by concatenating the first letter of the first name with the last name and an auto-incremented number."""
    if target.first and target.last:
        base_username = f"{target.first[0].lower()}{target.last.lower()}"
        existing_usernames = connection.execute(
            f"SELECT username FROM users WHERE username LIKE '{base_username}%'"
        ).fetchall()
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
    "user_projects",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("panda_users.id"), primary_key=True),
    Column("project_id", Integer, ForeignKey("panda_projects.id"), primary_key=True),
    Column("current", Boolean, default=True),
    Column("timestamp", Integer, default=dt.now(timezone.utc)),
)


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
            "round(json_extract(coordinates, '$.z') + base_thickness + height, 2)"
        ),
    )
    bottom: Mapped[float] = mapped_column(
        Float, Computed("round(json_extract(coordinates, '$.z') + base_thickness, 2)")
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
            "round(json_extract(coordinates, '$.z') + base_thickness + ((volume) / (3.1459 * radius * radius)), 2)"
        ),
    )
    contents: Mapped[dict] = mapped_column(JSON, default={})
    bottom: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(json_extract(coordinates, '$.z') + base_thickness + ((dead_volume) / (3.1459 * radius * radius)), 2)"
        ),
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
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated: Mapped[str] = mapped_column(
        String, nullable=False, default=dt.now(timezone.utc)
    )

    # Generated columns
    volume_height: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (volume / (3.1459 * radius * radius)), 2)"
        ),
    )
    top: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + height, 2)"
        ),
    )
    bottom: Mapped[float] = mapped_column(
        Float,
        Computed(
            "round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (dead_volume / (3.1459 * radius * radius)), 2)"
        ),
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


class VialStatus(VialsBase, Base):
    """VialStatus view model"""

    __tablename__ = "panda_vial_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[str] = mapped_column(String)
    category: Mapped[int] = mapped_column(Integer)
    viscosity_cp: Mapped[float] = mapped_column(Float)
    concentration: Mapped[float] = mapped_column(Float)
    density: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated: Mapped[str] = mapped_column(String, default=dt.now(timezone.utc))

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

    def __repr__(self):
        return f"<Wellplates(id={self.id}, type_id={self.type_id}, current={self.current})>"


class WellStatus(Base):
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

    def __repr__(self):
        return f"<WellStatus(plate_id={self.plate_id}, type_number={self.type_number}, well_id={self.well_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, experiment_id={self.experiment_id}, project_id={self.project_id}, volume={self.volume}, coordinates={self.coordinates}, capacity={self.capacity}, height={self.height})>"


class Queue(Base):
    """Queue view model"""

    __tablename__ = "panda_queue"
    experiment_id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    project_campaign_id = Column(Integer)
    priority = Column(Integer)
    process_type = Column(String)
    filename = Column(String)
    well_type = Column(String, name="well type")
    well_id = Column(String)
    status = Column(String)
    status_date = Column(String)

    def __repr__(self):
        return f"<Queue(experiment_id={self.experiment_id}, project_id={self.project_id}, priority={self.priority}, process_type={self.process_type}, filename={self.filename}, well_type={self.well_type}, well_id={self.well_id}, status={self.status}, status_date={self.status_date})>"


class MillConfig(Base):
    """
    Stores the JSON config for the grbl mill
    """

    __tablename__ = "panda_mill_config"
    id = Column(Integer, primary_key=True)
    config = Column(JSON, nullable=False)
    timestamp = Column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<MillConfig(id={self.id}, config={self.config})>"


class SystemVersions(Base):
    """SystemVersions table model"""

    __tablename__ = "panda_system_versions"
    id = Column(Integer, primary_key=True)
    mill = Column(Integer, nullable=False)
    pump = Column(String, default="00")
    potentiostat = Column(String, default="00")
    reference_electrode = Column(String, default="00")
    working_electrode = Column(String, default="00")
    wells = Column(String, default="00")
    pipette_adapter = Column(String, default="00")
    optics = Column(String, default="00")
    scale = Column(String, default="00")
    camera = Column(String, default="00")
    lens = Column(String, default="00")
    pin = Column(
        String,
        default=text(
            "(CAST (mill AS String) || ' ' || CAST (pump AS String) || ' ' || CAST (potentiostat AS String) || ' ' || CAST (reference_electrode AS String) || ' ' || CAST (working_electrode AS String) || ' ' || CAST (wells AS String) || ' ' || CAST (pipette_adapter AS String) || ' ' || CAST (optics AS String) || ' ' || CAST (scale AS String) || ' ' || CAST (camera AS String) || ' ' || CAST (lens AS String))"
        ),
    )

    def __repr__(self):
        return f"<SystemVersions(id={self.id}, mill={self.mill}, pump={self.pump}, potentiostat={self.potentiostat}, reference_electrode={self.reference_electrode}, working_electrode={self.working_electrode}, wells={self.wells}, pipette_adapter={self.pipette_adapter}, optics={self.optics}, scale={self.scale}, camera={self.camera}, lens={self.lens}, pin={self.pin})>"


class PotentiostatReadout(Base):
    """PotentiostatReadout table model"""

    __tablename__ = "potentiostat_readouts"

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
    #         f"SELECT * FROM potentiostat_techniques WHERE technique = '{target.technique}'"
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

    __tablename__ = "potentiostat_techniques"

    id = Column(Integer, primary_key=True)
    technique = Column(String, nullable=False)
    technique_description = Column(String, nullable=True)
    technique_params = Column(JSON, nullable=True)
    gamry_1010T = Column(Boolean, nullable=False)
    gamry_1010B = Column(Boolean, nullable=False)
    gamry_1010E = Column(Boolean, nullable=False)


class Tool(Base):
    """Tool table model"""

    __tablename__ = "panda_mill_tools"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    offset = Column(JSON, nullable=False)
    updated = Column(String, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<Tool(id={self.id}, name={self.name}, offset={self.offset}, updated={self.updated})>"

    @property
    def x(self):
        value: float = 0.0
        try:
            value = float(self.offset.get("x"))
        except ValueError:
            value = 0.0
        return value

    @property
    def y(self):
        value: float = 0.0
        try:
            value = float(self.offset.get("y"))
        except ValueError:
            value = 0.0
        return value

    @property
    def z(self):
        value: float = 0.0
        try:
            value = float(self.offset.get("z"))
        except ValueError:
            value = 0.0
        return value

    @x.setter
    def x(self, value: float):
        self.offset["x"] = value

    @y.setter
    def y(self, value: float):
        self.offset["y"] = value

    @z.setter
    def z(self, value: float):
        self.offset["z"] = value
