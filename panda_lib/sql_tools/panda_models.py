"""
SQLAlchemy models for the PANDA database
"""

# pylint: disable=too-few-public-methods, line-too-long
import datetime
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import Column, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, declarative_base, relationship
from sqlalchemy.sql.sqltypes import (DECIMAL, JSON, TEXT, Boolean, DateTime,
                                     Float)

Base = declarative_base()

from sqlalchemy.inspection import inspect


def model_to_dict(model):
    return {c.key: getattr(model, c.key)
            for c in inspect(model).mapper.column_attrs}

class Experiments(Base):
    """Experiments table model"""

    __tablename__ = "experiments"
    experiment_id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    project_campaign_id = Column(Integer)
    well_type = Column(Integer)
    protocol_id = Column(Integer)
    pin = Column(String)
    experiment_type = Column(Integer)
    jira_issue_key = Column(String)
    priority = Column(Integer, default=0)
    process_type = Column(Integer, default=0)
    filename = Column(String, default=None)
    created = Column(DateTime)
    updated = Column(DateTime, default=dt.now(timezone.utc))

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


class ExperimentResults(Base):
    """ExperimentResults table model"""

    __tablename__ = "experiment_results"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.experiment_id"))
    result_type = Column(String)
    result_value = Column(String)
    created = Column(DateTime, default=dt.now(timezone.utc))
    updated = Column(DateTime, default=dt.now(timezone.utc), onupdate=dt.now(timezone.utc))
    context = Column(String)

    def __repr__(self):
        return f"<ExperimentResults(id={self.id}, experiment_id={self.experiment_id}, result_type={self.result_type}, result_value={self.result_value}, created={self.created}, updated={self.updated}, context={self.context})>"


class ExperimentParameters(Base):
    """ExperimentParameters table model"""

    __tablename__ = "experiment_parameters"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.experiment_id"))
    parameter_name = Column(String)
    parameter_value = Column(String)
    created = Column(DateTime, default=dt.now)
    updated = Column(DateTime, default=dt.now, onupdate=dt.now(timezone.utc))

    def __repr__(self):
        return f"<ExperimentParameters(id={self.id}, experiment_id={self.experiment_id}, parameter_type={self.parameter_name}, parameter_value={self.parameter_value}, created={self.created}, updated={self.updated}, context={self.context})>"


class ExperimentGenerators(Base):
    """ExperimentGenerators table model"""

    __tablename__ = "generators"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    protocol_id = Column(Integer)
    name = Column(String)
    filepath = Column(String)

    def __repr__(self):
        return f"<ExperimentGenerators(id={self.id}, project_id={self.project_id}, protocol_id={self.protocol_id}, name={self.name}, filepath={self.filepath})>"


class MlPedotBestTestPoints(Base):
    """MlPedotBestTestPoints table model"""

    __tablename__ = "ml_pedot_best_test_points"
    model_id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, unique=True)
    best_test_point_scalar = Column(String)
    best_test_point_original = Column(String)
    best_test_point = Column(String)
    v_dep = Column(DECIMAL(18, 8))
    t_dep = Column(DECIMAL(18, 8))
    edot_concentration = Column(DECIMAL(18, 8))
    predicted_response = Column(DECIMAL(18, 8))
    standard_deviation = Column(DECIMAL(18, 8))
    models_current_rmse = Column(DECIMAL(18, 8))

    def __repr__(self):
        return f"<MlPedotBestTestPoints(model_id={self.model_id}, experiment_id={self.experiment_id}, best_test_point_scalar={self.best_test_point_scalar}, best_test_point_original={self.best_test_point_original}, best_test_point={self.best_test_point}, v_dep={self.v_dep}, t_dep={self.t_dep}, edot_concentration={self.edot_concentration}, predicted_response={self.predicted_response}, standard_deviation={self.standard_deviation}, models_current_rmse={self.models_current_rmse})>"


class MlPedotTrainingData(Base):
    """MlPedotTrainingData table model"""

    __tablename__ = "ml_pedot_training_data"
    id = Column(Integer, primary_key=True)
    delta_e = Column(DECIMAL(18, 8))
    voltage = Column(DECIMAL(18, 8))
    time = Column(DECIMAL(18, 8))
    bleach_cp = Column(DECIMAL(18, 8))
    concentration = Column(DECIMAL(18, 8))
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

    __tablename__ = "pipette"
    id = Column(Integer, primary_key=True)
    capacity_ul = Column(Float, nullable=False)
    capacity_ml = Column(Float, nullable=False)
    volume_ul = Column(Float, nullable=False)
    volume_ml = Column(Float, nullable=False)
    contents = Column(Text)
    updated = Column(DateTime, default=dt.now(timezone.utc))
    active = Column(Integer)  # 0 = inactive, 1 = active
    uses = Column(Integer, default=0)

    def __repr__(self):
        return f"<Pipette(id={self.id}, capacity_ul={self.capacity_ul}, capacity_ml={self.capacity_ml}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, contents={self.contents}, updated={self.updated})>"


class PipetteLog(Base):
    """PipetteLog table model"""

    __tablename__ = "pipette_log"
    id = Column(Integer, primary_key=True)
    pipette_id = Column(Integer, ForeignKey("pipette.id"))
    volume_ul = Column(Float, nullable=False)
    volume_ml = Column(Float, nullable=False)
    updated = Column(DateTime, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<PipetteLog(id={self.id}, pipette_id={self.pipette_id}, volume_ul={self.volume_ul}, volume_ml={self.volume_ml}, updated={self.updated})>"


class Projects(Base):
    """Projects table model"""

    __tablename__ = "projects"
    project_id = Column(Integer, primary_key=True)
    project_name = Column(String)
    # project_description = Column(String)
    # created = Column(DateTime)
    # updated = Column(DateTime, default=dt.now)

    def __repr__(self):
        return f"<Projects(project_id={self.project_id}, project_name={self.project_name})>"


class Protocols(Base):
    """Protocols table model"""

    __tablename__ = "protocols"
    id = Column(Integer, primary_key=True)
    project = Column(Integer, ForeignKey("projects.project_id"))
    name = Column(TEXT)
    filepath = Column(TEXT)


class SlackTickets(Base):
    """SlackTickets table model"""

    __tablename__ = "slack_tickets"
    msg_id = Column(String, primary_key=True, nullable=False, unique=True)
    channel_id = Column(String, nullable=False)
    message = Column(String, nullable=False)
    response = Column(Integer)
    timestamp = Column(String)
    addressed_timestamp = Column(String)
    db_timestamp = Column(String, default=text("(datetime('now', 'localtime'))"))

    def __repr__(self):
        return f"<SlackTickets(msg_id={self.msg_id}, channel_id={self.channel_id}, message={self.message}, response={self.response}, timestamp={self.timestamp}, addressed_timestamp={self.addressed_timestamp}, db_timestamp={self.db_timestamp})>"


class SystemStatus(Base):
    """SystemStatus table model"""

    __tablename__ = "system_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String, nullable=False)
    comment = Column(String)
    status_time = Column(DateTime, default=dt.now(timezone.utc))
    test_mode = Column(Boolean)

    def __repr__(self):
        return f"<SystemStatus(id={self.id}, status={self.status}, comment={self.comment}, status_time={self.status_time}, test_mode={self.test_mode})>"


class Users(Base):
    """Users table model"""

    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    email = Column(String)
    created = Column(DateTime)
    updated = Column(DateTime, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<Users(user_id={self.user_id}, username={self.username}, password={self.password}, email={self.email}, created={self.created}, updated={self.updated})>"


class Vials(Base):
    """
    Vials table model
    
    Categories: 0 = Stock, 1 = Waste, 2 = Reagent, 3 = Unknown
    """

    __tablename__ = "vials"
    id = Column(Integer, primary_key=True)
    position = Column(String)
    contents = Column(String)
    viscosity_cp = Column(Float)
    concentration = Column(Float)
    density = Column(Float)
    category = Column(Integer)
    radius = Column(Integer)
    height = Column(Integer)
    depth = Column(Integer)
    name = Column(String)
    volume = Column(Float)
    capacity = Column(Integer)
    contamination = Column(Integer)
    vial_coordinates = Column(String)
    updated = Column(DateTime, default = dt.now(timezone.utc))

    def __repr__(self):
        return f"<Vials(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, depth={self.depth}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, vial_coordinates={self.vial_coordinates}, updated={self.updated})>"


class WellHx(Base):
    """WellHx table model"""

    __tablename__ = "well_hx"
    plate_id = Column(Integer, primary_key=True)
    well_id = Column(String, primary_key=True)
    experiment_id = Column(Integer)
    project_id = Column(Integer)
    status = Column(String)
    status_date = Column(DateTime, default=dt.now(timezone.utc))
    contents = Column(JSON)
    volume = Column(Float)
    coordinates = Column(JSON)
    updated = Column(DateTime, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<WellHx(plate_id={self.plate_id}, well_id={self.well_id}, experiment_id={self.experiment_id}, project_id={self.project_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, volume={self.volume}, coordinates={self.coordinates}, updated={self.updated})>"


class WellTypes(Base):
    """WellTypes table model"""

    __tablename__ = "well_types"
    id: int = Column(Integer, primary_key=True)
    substrate: str = Column(String)
    gasket: str = Column(String)
    count: int = Column(Integer)
    rows: str = Column(String)
    cols: int = Column(Integer)
    shape: str = Column(String)
    radius_mm: float = Column(Float)
    y_spacing: float = Column(Float)
    x_spacing: float = Column(Float)
    gasket_length_mm: float = Column(Float)
    gasket_width_mm: float = Column(Float)
    gasket_height_mm: float = Column(Float)
    x_offset: float = Column(Float)
    y_offset: float = Column(Float)
    max_liquid_height_mm: float = Column(Float)
    capacity_ul: float = Column(Float)

    def __repr__(self):
        return f"<WellTypes(id={self.id}, substrate={self.substrate}, gasket={self.gasket}, count={self.count}, shape={self.shape}, radius_mm={self.radius_mm}, offset_mm={self.y_spacing}, height_mm={self.gasket_height_mm}, max_liquid_height_mm={self.max_liquid_height_mm}, capacity_ul={self.capacity_ul})>"


class WellPlates(Base):
    """WellPlates table model"""

    __tablename__ = "wellplates"
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey("well_types.id"))
    current = Column(Boolean, default=False)
    a1_x = Column(Float)
    a1_y = Column(Float)
    orientation = Column(Integer)
    rows = Column(String)
    cols = Column(Integer)
    z_bottom = Column(Float)
    z_top = Column(Float)
    echem_height = Column(Float)
    image_height = Column(Float)

    def __repr__(self):
        return f"<WellPlates(id={self.id}, type_id={self.type_id}, current={self.current})>"


class Queue(Base):
    """Queue view model"""

    __tablename__ = "queue"
    experiment_id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    priority = Column(Integer)
    process_type = Column(String)
    filename = Column(String)
    well_type = Column(String, name="well type")
    well_id = Column(String)
    status = Column(String)
    status_date = Column(DateTime)

    def __repr__(self):
        return f"<Queue(experiment_id={self.experiment_id}, project_id={self.project_id}, priority={self.priority}, process_type={self.process_type}, filename={self.filename}, well_type={self.well_type}, well_id={self.well_id}, status={self.status}, status_date={self.status_date})>"


class WellStatus(Base):
    """WellStatus view model"""

    __tablename__ = "well_status"
    plate_id = Column(Integer, primary_key=True)
    type_number = Column(Integer)
    well_id = Column(String, primary_key=True)
    status = Column(String)
    status_date = Column(DateTime)
    contents = Column(JSON)
    experiment_id = Column(Integer)
    project_id = Column(Integer)
    volume = Column(Float)
    coordinates = Column(JSON)
    capacity = Column(Float)
    height = Column(Float)

    def __repr__(self):
        return f"<WellStatus(plate_id={self.plate_id}, type_number={self.type_number}, well_id={self.well_id}, status={self.status}, status_date={self.status_date}, contents={self.contents}, experiment_id={self.experiment_id}, project_id={self.project_id}, volume={self.volume}, coordinates={self.coordinates}, capacity={self.capacity}, height={self.height})>"

class MillConfig(Base):
    """
    Stores the JSON config for the grbl mill
    """

    __tablename__ = "mill_config"
    id = Column(Integer, primary_key=True)
    config = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<MillConfig(id={self.id}, config={self.config})>"

class SystemVersions(Base):
    """SystemVersions table model"""

    __tablename__ = "system_versions"
    id = Column(Integer, primary_key=True)
    mill = Column(Integer, nullable=False)
    pump = Column(Text, default='00')
    potentiostat = Column(Text, default='00')
    reference_electrode = Column(Text, default='00')
    working_electrode = Column(Text, default='00')
    wells = Column(Text, default='00')
    pipette_adapter = Column(Text, default='00')
    optics = Column(Text, default='00')
    scale = Column(Text, default='00')
    camera = Column(Text, default='00')
    lens = Column(Text, default='00')
    pin = Column(Text, default=text("(CAST (mill AS TEXT) || ' ' || CAST (pump AS TEXT) || ' ' || CAST (potentiostat AS TEXT) || ' ' || CAST (reference_electrode AS TEXT) || ' ' || CAST (working_electrode AS TEXT) || ' ' || CAST (wells AS TEXT) || ' ' || CAST (pipette_adapter AS TEXT) || ' ' || CAST (optics AS TEXT) || ' ' || CAST (scale AS TEXT) || ' ' || CAST (camera AS TEXT) || ' ' || CAST (lens AS TEXT))"))

    def __repr__(self):
        return f"<SystemVersions(id={self.id}, mill={self.mill}, pump={self.pump}, potentiostat={self.potentiostat}, reference_electrode={self.reference_electrode}, working_electrode={self.working_electrode}, wells={self.wells}, pipette_adapter={self.pipette_adapter}, optics={self.optics}, scale={self.scale}, camera={self.camera}, lens={self.lens}, pin={self.pin})>"

class VialStatus(Base):
    """VialStatus view model"""

    __tablename__ = "vial_status"
    id = Column(Integer, primary_key=True)
    position = Column(String)
    contents = Column(String)
    viscosity_cp = Column(Float)
    concentration = Column(Float)
    density = Column(Float)
    category = Column(Integer)
    radius = Column(Integer)
    height = Column(Integer)
    depth = Column(Integer)
    name = Column(String)
    volume = Column(Float)
    capacity = Column(Integer)
    contamination = Column(Integer)
    vial_coordinates = Column(String)
    updated = Column(DateTime, default=dt.now(timezone.utc))

    def __repr__(self):
        return f"<VialStatus(id={self.id}, position={self.position}, contents={self.contents}, viscosity_cp={self.viscosity_cp}, concentration={self.concentration}, density={self.density}, category={self.category}, radius={self.radius}, height={self.height}, depth={self.depth}, name={self.name}, volume={self.volume}, capacity={self.capacity}, contamination={self.contamination}, vial_coordinates={self.vial_coordinates}, updated={self.updated})>"
