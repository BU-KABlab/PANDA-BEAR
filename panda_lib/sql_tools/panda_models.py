"""
SQLAlchemy models for the PANDA database
"""

# pylint: disable=too-few-public-methods, line-too-long
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Column, ForeignKey, text, event, Table
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped, declarative_base, relationship
from sqlalchemy.sql.sqltypes import BIGINT, INTEGER, JSON, REAL, TEXT, BOOLEAN

Base = declarative_base()


def model_to_dict(model):
    return {c.key: getattr(model, c.key) for c in inspect(model).mapper.column_attrs}


class Experiments(Base):
    """Experiments table model"""

    __tablename__ = "experiments"
    experiment_id = Column(BIGINT, primary_key=True)
    project_id = Column(INTEGER)
    project_campaign_id = Column(INTEGER)
    well_type = Column(INTEGER)
    protocol_id = Column(INTEGER)
    pin = Column(TEXT)
    experiment_type = Column(INTEGER)
    jira_issue_key = Column(TEXT)
    priority = Column(INTEGER, default=0)
    process_type = Column(INTEGER, default=0)
    filename = Column(TEXT, default=None)
    created = Column(TEXT)
    updated = Column(TEXT, default=dt.now(timezone.utc))

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

    __tablename__ = "experiment_status"
    experiment_id = Column(INTEGER, primary_key=True)
    status = Column(TEXT)

    def __repr__(self):
        return f"<ExperimentStatus(experiment_id={self.experiment_id}, status={self.status})>"


class ExperimentResults(Base):
    """ExperimentResults table model"""

    __tablename__ = "experiment_results"
    id = Column(INTEGER, primary_key=True)
    experiment_id = Column(INTEGER, ForeignKey("experiments.experiment_id"))
    result_type = Column(TEXT)
    result_value = Column(TEXT)
    created = Column(TEXT, default=dt.now(timezone.utc))
    updated = Column(TEXT, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc))
    context = Column(TEXT)

    def __repr__(self):
        return f"<ExperimentResults(id={self.id}, experiment_id={self.experiment_id}, result_type={self.result_type}, result_value={self.result_value}, created={self.created}, updated={self.updated}, context={self.context})>"


class ExperimentParameters(Base):
    """ExperimentParameters table model"""

    __tablename__ = "experiment_parameters"
    id = Column(INTEGER, primary_key=True)
    experiment_id = Column(INTEGER, ForeignKey("experiments.experiment_id"))
    parameter_name = Column(TEXT)
    parameter_value = Column(TEXT)
    created = Column(TEXT, default=dt.now)
    updated = Column(TEXT, default=dt.now, onupdate=dt.now(timezone.utc))

    def __repr__(self):
        return f"<ExperimentParameters(id={self.id}, experiment_id={self.experiment_id}, parameter_type={self.parameter_name}, parameter_value={self.parameter_value}, created={self.created}, updated={self.updated}, context={self.context})>"


class ExperimentGenerators(Base):
    """ExperimentGenerators table model"""

    __tablename__ = "generators"
    id = Column(INTEGER, primary_key=True)
    project_id = Column(INTEGER)
    protocol_id = Column(INTEGER)
    name = Column(TEXT)
    filepath = Column(TEXT)

    def __repr__(self):
        return f"<ExperimentGenerators(id={self.id}, project_id={self.project_id}, protocol_id={self.protocol_id}, name={self.name}, filepath={self.filepath})>"


class MlPedotBestTestPoints(Base):
    """MlPedotBestTestPoints table model"""

    __tablename__ = "ml_pedot_best_test_points"
    model_id = Column(INTEGER, primary_key=True)
    experiment_id = Column(INTEGER, unique=True)
    best_test_point_scalar = Column(TEXT)
    best_test_point_original = Column(TEXT)
    best_test_point = Column(TEXT)
    v_dep = Column(REAL(18, 8))
    t_dep = Column(REAL(18, 8))
    edot_concentration = Column(REAL(18, 8))
    predicted_response = Column(REAL(18, 8))
    standard_deviation = Column(REAL(18, 8))
    models_current_rmse = Column(REAL(18, 8))

    def __repr__(self):
        return f"<MlPedotBestTestPoints(model_id={self.model_id}, experiment_id={self.experiment_id}, best_test_point_scalar={self.best_test_point_scalar}, best_test_point_original={self.best_test_point_original}, best_test_point={self.best_test_point}, v_dep={self.v_dep}, t_dep={self.t_dep}, edot_concentration={self.edot_concentration}, predicted_response={self.predicted_response}, standard_deviation={self.standard_deviation}, models_current_rmse={self.models_current_rmse})>"


class MlPedotTrainingData(Base):
    """MlPedotTrainingData table model"""

    __tablename__ = "ml_pedot_training_data"
    id = Column(INTEGER, primary_key=True)
    delta_e = Column(REAL(18, 8))
    voltage = Column(REAL(18, 8))
    time = Column(REAL(18, 8))
    bleach_cp = Column(REAL(18, 8))
    concentration = Column(REAL(18, 8))
    experiment_id = Column(INTEGER)

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

    __tablename__ = "pipette"
    id = Column(INTEGER, primary_key=True)
    capacity_ul = Column(REAL, nullable=False)
    capacity_ml = Column(REAL, nullable=False)
    volume_ul = Column(REAL, nullable=False)
    volume_ml = Column(REAL, nullable=False)
    contents = Column(TEXT)
    updated = Column(TEXT, default=dt.now(timezone.utc))
    active = Column(INTEGER)  # 0 = inactive, 1 = active
    uses = Column(INTEGER, default=0)

    def __repr__(self):
        return f"<Pipette(id={self.id}, capacity_ul={self.capacity_ul}, capacity_ml={self.capacity_ml}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, contents={self.contents}, updated={self.updated})>"


class PipetteLog(Base):
    """PipetteLog table model"""

    __tablename__ = "pipette_log"
    id = Column(INTEGER, primary_key=True)
    pipette_id = Column(INTEGER, ForeignKey("pipette.id"))
    volume_ul = Column(REAL, nullable=False)
    volume_ml = Column(REAL, nullable=False)
    updated = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<PipetteLog(id={self.id}, pipette_id={self.pipette_id}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, updated={self.updated})>"


class Projects(Base):
    """Projects table model"""

    __tablename__ = "projects"
    id = Column(INTEGER, primary_key=True)
    project_name = Column(TEXT)
    # project_description = Column(TEXT)
    # created = Column(TEXT)
    # updated = Column(TEXT, default=dt.now)

    def __repr__(self):
        return f"<Projects(project_id={self.project_id}, project_name={self.project_name})>"


class Protocols(Base):
    """Protocols table model"""

    __tablename__ = "protocols"
    id = Column(INTEGER, primary_key=True)
    project = Column(INTEGER)
    name = Column(TEXT)
    filepath = Column(TEXT)


class SlackTickets(Base):
    """SlackTickets table model"""

    __tablename__ = "slack_tickets"
    msg_id = Column(TEXT, primary_key=True, nullable=False, unique=True)
    channel_id = Column(TEXT, nullable=False)
    message = Column(TEXT, nullable=False)
    response = Column(INTEGER)
    timestamp = Column(TEXT)
    addressed_timestamp = Column(TEXT)
    db_timestamp = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<SlackTickets(msg_id={self.msg_id}, channel_id={self.channel_id}, message={self.message}, response={self.response}, timestamp={self.timestamp}, addressed_timestamp={self.addressed_timestamp}, db_timestamp={self.db_timestamp})>"


class SystemStatus(Base):
    """SystemStatus table model"""

    __tablename__ = "system_status"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    status = Column(TEXT, nullable=False)
    comment = Column(TEXT)
    status_time = Column(TEXT, default=dt.now(timezone.utc))
    test_mode = Column(BOOLEAN)

    def __repr__(self):
        return f"<SystemStatus(id={self.id}, status={self.status}, comment={self.comment}, status_time={self.status_time}, test_mode={self.test_mode})>"

class Users(Base):
    """Users table model"""

    __tablename__ = "users"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    first = Column(TEXT, nullable=False)
    last = Column(TEXT, nullable=False)
    username = Column(TEXT, unique=True)
    password = Column(TEXT, nullable=False)
    email = Column(TEXT, nullable=False)
    active = Column(BOOLEAN, default=True)
    created = Column(TEXT, default=dt.now(timezone.utc))
    updated = Column(TEXT, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc))

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
event.listen(Users, 'before_insert', generate_username)

# Junction table for the many-to-many relationship between users and projects
user_projects = Table('user_projects', Base.metadata,
    Column('user_id', INTEGER, ForeignKey('users.id'), primary_key=True),
    Column('project_id', INTEGER, ForeignKey('projects.id'), primary_key=True),
    Column('current', BOOLEAN, default=True),
    Column('timestamp', INTEGER, default=dt.now(timezone.utc))
)

class Vials(Base):
    """
    Vials table model

    Categories: 0 = Stock, 1 = Waste, 2 = Reagent, 3 = Unknown
    """

    __tablename__ = "vials"
    id = Column(INTEGER, primary_key=True)
    position = Column(TEXT)
    contents = Column(TEXT)
    viscosity_cp = Column(REAL)
    concentration = Column(REAL)
    density = Column(REAL)
    category = Column(INTEGER)
    radius = Column(INTEGER)
    height = Column(INTEGER)
    depth = Column(INTEGER)
    name = Column(TEXT)
    volume = Column(REAL)
    capacity = Column(INTEGER)
    contamination = Column(INTEGER)
    vial_coordinates = Column(TEXT)
    updated = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<Vials(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, depth={self.depth}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, vial_coordinates={self.vial_coordinates}, updated={self.updated})>"


class WellHx(Base):
    """WellHx table model"""

    __tablename__ = "well_hx"
    plate_id = Column(INTEGER, primary_key=True)
    well_id = Column(TEXT, primary_key=True)
    experiment_id = Column(INTEGER)
    project_id = Column(INTEGER)
    status = Column(TEXT)
    status_date = Column(TEXT, default=dt.now(timezone.utc))
    contents = Column(JSON)
    volume = Column(REAL)
    coordinates = Column(JSON)
    updated = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<WellHx(plate_id={self.plate_id}, well_id={self.well_id}, experiment_id={self.experiment_id}, project_id={self.project_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, volume={self.volume}, coordinates={self.coordinates}, updated={self.updated})>"


class PlateTypes(Base):
    """WellTypes table model"""

    __tablename__ = "plate_types"
    id: int = Column(INTEGER, primary_key=True)
    substrate: str = Column(TEXT)
    gasket: str = Column(TEXT)
    count: int = Column(INTEGER)
    rows: str = Column(TEXT)
    cols: int = Column(INTEGER)
    shape: str = Column(TEXT)
    radius_mm: float = Column(REAL)
    y_spacing: float = Column(REAL)
    x_spacing: float = Column(REAL)
    gasket_length_mm: float = Column(REAL)
    gasket_width_mm: float = Column(REAL)
    gasket_height_mm: float = Column(REAL)
    x_offset: float = Column(REAL)
    y_offset: float = Column(REAL)
    max_liquid_height_mm: float = Column(REAL)
    capacity_ul: float = Column(REAL)

    def __repr__(self):
        return f"<WellTypes(id={self.id}, substrate={self.substrate}, gasket={self.gasket}, count={self.count}, shape={self.shape}, radius_mm={self.radius_mm}, offset_mm={self.y_spacing}, height_mm={self.gasket_height_mm}, max_liquid_height_mm={self.max_liquid_height_mm}, capacity_ul={self.capacity_ul})>"


class WellPlates(Base):
    """WellPlates table model"""

    __tablename__ = "wellplates"
    id = Column(INTEGER, primary_key=True)
    type_id = Column(INTEGER, ForeignKey("plate_types.id"))
    current = Column(BOOLEAN, default=False)
    a1_x = Column(REAL)
    a1_y = Column(REAL)
    orientation = Column(INTEGER)
    rows = Column(TEXT)
    cols = Column(INTEGER)
    z_bottom = Column(REAL)
    z_top = Column(REAL)
    echem_height = Column(REAL)
    image_height = Column(REAL)

    def __repr__(self):
        return f"<WellPlates(id={self.id}, type_id={self.type_id}, current={self.current})>"


class Queue(Base):
    """Queue view model"""

    __tablename__ = "queue"
    experiment_id = Column(INTEGER, primary_key=True)
    project_id = Column(INTEGER)
    project_campaign_id = Column(INTEGER)
    priority = Column(INTEGER)
    process_type = Column(TEXT)
    filename = Column(TEXT)
    well_type = Column(TEXT, name="well type")
    well_id = Column(TEXT)
    status = Column(TEXT)
    status_date = Column(TEXT)

    def __repr__(self):
        return f"<Queue(experiment_id={self.experiment_id}, project_id={self.project_id}, priority={self.priority}, process_type={self.process_type}, filename={self.filename}, well_type={self.well_type}, well_id={self.well_id}, status={self.status}, status_date={self.status_date})>"


class WellStatus(Base):
    """WellStatus view model"""

    __tablename__ = "well_status"
    plate_id = Column(INTEGER, primary_key=True)
    type_number = Column(INTEGER)
    well_id = Column(TEXT, primary_key=True)
    status = Column(TEXT)
    status_date = Column(TEXT)
    contents = Column(JSON)
    experiment_id = Column(INTEGER)
    project_id = Column(INTEGER)
    volume = Column(REAL)
    coordinates = Column(JSON)
    capacity = Column(REAL)
    height = Column(REAL)

    def __repr__(self):
        return f"<WellStatus(plate_id={self.plate_id}, type_number={self.type_number}, well_id={self.well_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, experiment_id={self.experiment_id}, project_id={self.project_id}, volume={self.volume}, coordinates={self.coordinates}, capacity={self.capacity}, height={self.height})>"


class MillConfig(Base):
    """
    Stores the JSON config for the grbl mill
    """

    __tablename__ = "mill_config"
    id = Column(INTEGER, primary_key=True)
    config = Column(JSON, nullable=False)
    timestamp = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<MillConfig(id={self.id}, config={self.config})>"


class SystemVersions(Base):
    """SystemVersions table model"""

    __tablename__ = "system_versions"
    id = Column(INTEGER, primary_key=True)
    mill = Column(INTEGER, nullable=False)
    pump = Column(TEXT, default="00")
    potentiostat = Column(TEXT, default="00")
    reference_electrode = Column(TEXT, default="00")
    working_electrode = Column(TEXT, default="00")
    wells = Column(TEXT, default="00")
    pipette_adapter = Column(TEXT, default="00")
    optics = Column(TEXT, default="00")
    scale = Column(TEXT, default="00")
    camera = Column(TEXT, default="00")
    lens = Column(TEXT, default="00")
    pin = Column(
        TEXT,
        default=text(
            "(CAST (mill AS TEXT) || ' ' || CAST (pump AS TEXT) || ' ' || CAST (potentiostat AS TEXT) || ' ' || CAST (reference_electrode AS TEXT) || ' ' || CAST (working_electrode AS TEXT) || ' ' || CAST (wells AS TEXT) || ' ' || CAST (pipette_adapter AS TEXT) || ' ' || CAST (optics AS TEXT) || ' ' || CAST (scale AS TEXT) || ' ' || CAST (camera AS TEXT) || ' ' || CAST (lens AS TEXT))"
        ),
    )

    def __repr__(self):
        return f"<SystemVersions(id={self.id}, mill={self.mill}, pump={self.pump}, potentiostat={self.potentiostat}, reference_electrode={self.reference_electrode}, working_electrode={self.working_electrode}, wells={self.wells}, pipette_adapter={self.pipette_adapter}, optics={self.optics}, scale={self.scale}, camera={self.camera}, lens={self.lens}, pin={self.pin})>"


class VialStatus(Base):
    """VialStatus view model"""

    __tablename__ = "vial_status"
    id = Column(INTEGER, primary_key=True)
    position = Column(TEXT)
    contents = Column(TEXT)
    viscosity_cp = Column(REAL)
    concentration = Column(REAL)
    density = Column(REAL)
    category = Column(INTEGER)
    radius = Column(INTEGER)
    height = Column(INTEGER)
    depth = Column(INTEGER)
    name = Column(TEXT)
    volume = Column(REAL)
    capacity = Column(INTEGER)
    contamination = Column(INTEGER)
    vial_coordinates = Column(TEXT)
    updated = Column(TEXT, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<VialStatus(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, depth={self.depth}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, vial_coordinates={self.vial_coordinates}, updated={self.updated})>"
