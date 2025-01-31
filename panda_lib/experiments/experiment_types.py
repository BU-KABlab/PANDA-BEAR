import importlib.util
import json
from datetime import datetime, timezone
from typing import Callable, List, Optional, Union, get_type_hints

from pydantic import ConfigDict, Field, RootModel, field_validator
from pydantic.dataclasses import dataclass

from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    Experiments,
    ExperimentStatusView,
    WellModel,
    Wellplates,
)

# from panda_lib.sql_tools.sql_utilities import (execute_sql_command,
#                                                 execute_sql_command_no_return)
from panda_lib.sql_tools.sql_wellplate import get_well_by_id
from shared_utilities.config.config_tools import read_config

# from panda_lib.sql_tools.sql_utilities import (execute_sql_command,
#                                                 execute_sql_command_no_return)
from shared_utilities.db_setup import SessionLocal
from shared_utilities.log_tools import setup_default_logger

from .experiment_parameters import ExperimentParameterRecord
from .experiment_status import ExperimentStatus
from .results import ExperimentResult

global_logger = setup_default_logger(log_name="panda")
experiment_logger = setup_default_logger(log_name="experiment_logger")
config = read_config()


def load_analysis_script(script_path: str) -> Callable:
    """Load a script from a file and return the analyze function"""
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Check that the module has an analyze function
    if not hasattr(module, "analyze"):
        raise AttributeError(f"Module {script_path} does not have an analyze function")
    return module.analyze


@dataclass(config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True))
class ExperimentBase:
    """Define the common data used to run and define an experiment"""

    experiment_id: int = Field(
        default=0,
        title="Experiment ID",
        description="Unique identifier for the experiment",
    )
    experiment_name: str = Field(
        default="experiment",
        title="Experiment Name",
        description="Name of the experiment",
    )
    protocol_id: Union[int, str] = Field(
        default=999,
        title="Protocol ID",
        description="Identifier for the protocol used in the experiment",
    )
    priority: Optional[int] = Field(
        default=0, title="Priority", description="Priority level of the experiment"
    )
    well_id: Optional[str] = Field(
        default="A1",
        title="Well ID",
        description="Identifier for the well used in the experiment",
    )
    pin: Union[str, int] = Field(
        default=0,
        title="PIN",
        description="Personal Identification Number associated with the experiment",
    )
    project_id: int = Field(
        default=999,
        title="Project ID",
        description="Identifier for the project associated with the experiment",
    )
    solutions: dict[str, dict[str, Union[int, float]]] = Field(
        default={},
        title="Solutions",
        description="Dictionary of solutions used in the experiment",
    )
    plate_type_number: int = Field(
        default=None,
        title="Plate Type Number",
        description="Type number of the wellplate used in the experiment",
    )
    pumping_rate: float = Field(
        default=0.3,
        title="Pumping Rate",
        description="Rate at which the solution is pumped",
    )
    status: ExperimentStatus = Field(
        default=ExperimentStatus.NEW,
        title="Status",
        description="Current status of the experiment",
    )
    status_date: datetime = Field(
        default_factory=datetime.now,
        title="Status Date",
        description="Date and time when the status was last updated",
    )
    filename: str = Field(
        default=f"{experiment_id}_{experiment_name}",
        title="Filename",
        description="Filename associated with the experiment data",
    )
    results: Optional[ExperimentResult] = Field(
        default=None, title="Results", description="Results of the experiment"
    )
    project_campaign_id: int = Field(
        default=0,
        title="Project Campaign ID",
        description="Identifier for the project campaign associated with the experiment",
    )
    protocol_type: int = Field(
        default=1,
        title="Protocol Type",
        description="Type of protocol used in the experiment",
        deprecated=True,
    )
    plate_id: Optional[int] = Field(
        default=None,
        title="Plate ID",
        description="Identifier for the plate used in the experiment",
    )
    override_well_selection: int = Field(
        default=0,
        title="Override Well Selection",
        description="Flag to override well selection (0 is normal, 1 is override)",
    )
    process_type: Optional[int] = Field(
        default=1,
        title="Process Type",
        description="Type of process used in the experiment",
        deprecated=True,
    )
    jira_issue_key: Optional[str] = Field(
        default=None,
        title="JIRA Issue Key",
        description="JIRA issue key associated with the experiment",
        deprecated=True,
    )
    experiment_type: int = Field(
        default=0,
        title="Experiment Type",
        description="Type of experiment",
        deprecated=True,
    )
    well: object = Field(
        default=None,
        title="Well",
        description="Well object associated with the experiment",
    )
    analyzer: Union[Callable, str, None] = Field(
        default=None,
        title="Analyzer",
        description="Analyzer function or script used for the experiment",
    )
    generator: Union[Callable, str, None] = Field(
        default=None,
        title="Generator",
        description="Generator function or script used for the experiment",
    )
    analysis_id: int = Field(
        default=0,
        title="Analysis ID",
        description="Identifier for the analysis associated with the experiment",
    )
    needs_analysis: int = Field(
        default=0,
        title="Needs Analysis",
        description="Flag indicating if the experiment needs analysis",
    )
    steps: int = Field(
        default=0,
        title="Steps",
        description="Number of steps completed in the experiment",
        exclude=True,
    )

    @field_validator("experiment_name")
    def validate_experiment_name(cls, value):
        if value:
            return value.lower()
        return None

    def __post_init__(self):
        # Validate that all dictionary keys are lowercase
        if self.solutions is None:
            self.solutions = {}
        else:
            self.solutions = {
                key.lower(): value for key, value in self.solutions.items()
            }

    @property
    def experiment_identifier(self):
        """
        For consistent naming of experiment files

        Template: {experiment_id}_{experiment_name}_{plate_id}_{well_id}
        """
        return f"{self.experiment_id}_{self.experiment_name}_{self.plate_id}_{self.well_id}"

    def run_analysis(self):
        """Run the analysis"""
        if isinstance(self.analyzer, str):
            # Load and execute the script
            analysis_function = load_analysis_script(self.analyzer)
            analysis_function(
                experiment_id=self.experiment_id, add_to_training_data=True
            )
        elif callable(self.analyzer):
            # Directly call the function
            self.analyzer(experiment_id=self.experiment_id, add_to_training_data=True)

        else:
            experiment_logger.debug(
                "\n No analysis function provided for experiment %s\n",
                self.experiment_id,
            )

    def run_generator(self) -> None:
        """Run the generator."""
        if isinstance(self.generator, str):
            # Load and execute the script
            generator_function = load_analysis_script(self.generator)
            generator_function()
        elif callable(self.generator):
            # Directly call the function
            self.generator()

        else:
            experiment_logger.debug(
                "\n No generator function provided for experiment %s\n",
                self.experiment_id,
            )

    # FIXME: separate the set status, and set status and save methods from the experimentbase. The experiment base should just be a dataclass
    # What could be an alternative is that there is a wrapper class that has the set status and set status and save methods using what
    # Method that the project chooses to use to save the data to the database
    def set_status(self, new_status: ExperimentStatus) -> None:
        """Set the status of the experiment."""
        self.status = new_status
        self.status_date = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")

    def set_status_and_save(self, new_status: ExperimentStatus) -> None:
        """Set the status and status date of the experiment."""

        self.status = new_status
        self.status_date = datetime.now().isoformat(timespec="seconds")

        if not self.well or not isinstance(self.well, object):
            experiment_logger.warning("Well object not set. Checking for Well ID")
            if self.well_id:
                self.well = get_well_by_id(self.well_id)
            else:
                experiment_logger.error("Well ID not set, cannot save status")
                return

        # Save the well to the database
        if self.well:
            self.well.update_status(self.status)
            # sql_wellplate.save_well_to_db(self.well)

        else:
            experiment_logger.debug(
                "Well object not set. Saving to db via alternative method"
            )
            _update_experiment_status(self)

        # Save the experiment to the database
        _update_experiment(self)

    def is_same_id(self, other) -> bool:
        """Check if two experiments have the same id."""

        return self.experiment_id == other.id

    def is_same_well_id(self, other) -> bool:
        """Check if two experiments have the same well id."""

        return self.well_id == other.well_id and self.plate_id == other.plate_id

    ## other check if same methods

    def generate_parameter_list(self) -> list[ExperimentParameterRecord]:
        """Turn the experiment object into a list of individual experiment parameter table records"""
        all_parameters = [
            ExperimentParameterRecord(
                self.experiment_id, parameter_type, parameter_value
            )
            for parameter_type, parameter_value in self.__dict__.items()
        ]

        # Remove project_id, project_campaign_id, well_type,protocol_id, pin, experiment_type, jira_issue_key, priority, process_type, filename, status, status_date, results, well
        all_parameters = [
            parameter
            for parameter in all_parameters
            if parameter.parameter_name
            not in [
                "project_id",
                "project_campaign_id",
                "well_type",
                "protocol_id",
                "protocol_type",  # depreciated
                "pin",
                "experiment_type",
                "jira_issue_key",
                "priority",
                "process_type",
                "filename",
                "status",
                "status_date",
                "results",
                "well",
                "well_id",
                "experiment_id",
            ]
        ]

        return all_parameters

    # def generate_result_list(self) -> list[ExperimentResultsRecord]:

    def map_parameter_list_to_experiment(
        self, parameter_list: list[ExperimentParameterRecord]
    ):
        """Turn the parameter list from the sql database into to an experiment object"""

        def find_attribute_in_hierarchy(cls, attr):
            """Recursively search for an attribute in a class and its subclasses"""
            if hasattr(cls, attr):
                return cls
            for subclass in cls.__subclasses__():
                result = find_attribute_in_hierarchy(subclass, attr)
                if result is not None:
                    return result
            return None

        for parameter in parameter_list:
            # parameter = ExperimentParameterRecord(
            #     experiment_id=parameter.experiment_id,
            #     parameter_name=parameter.parameter_name,
            #     parameter_value=parameter.parameter_value,
            # )
            try:
                attribute_type = _get_all_type_hints(type(self))[
                    parameter.parameter_name
                ]
            except KeyError as exc:
                # The attribute is not in ExperimentBase, check in the class hierarchy
                cls = find_attribute_in_hierarchy(
                    self.__class__, parameter.parameter_name
                )
                if cls is not None:
                    attribute_type = _get_all_type_hints(cls)[parameter.parameter_name]
                else:
                    experiment_logger.debug(
                        "Attribute %s not found in class hierarchy",
                        parameter.parameter_name,
                    )
                    error_message = f"Attribute {parameter.parameter_name} not found in class hierarchy"
                    raise AttributeError(error_message) from exc

            if isinstance(
                attribute_type, type(Union)
            ):  # Check if the type hint is a Union
                # The attribute can be one of several types
                possible_types = attribute_type.__args__
                for possible_type in possible_types:
                    # Try to convert the parameter value to each possible type
                    try:
                        parameter.parameter_value = possible_type(
                            parameter.parameter_value
                        )
                        break  # If the conversion succeeds, stop trying other types
                    except ValueError:
                        pass  # If the conversion fails, try the next type
            elif (
                hasattr(attribute_type, "_name") and attribute_type._name == "Optional"
            ):  # Check if the type hint is Optional
                # The attribute can be None or the specified type
                possible_type = attribute_type.__args__[0]
                if parameter.parameter_value is None:
                    parameter.parameter_value = None
                else:
                    # Try to convert the parameter value to the specified type
                    parameter.parameter_value = possible_type(parameter.parameter_value)

            elif attribute_type is int:
                parameter.parameter_value = int(parameter.parameter_value)
            elif attribute_type in [float, float]:
                parameter.parameter_value = float(parameter.parameter_value)
            elif attribute_type is bool:
                parameter.parameter_value = bool(parameter.parameter_value)
            elif attribute_type is str:
                parameter.parameter_value = str(parameter.parameter_value)
            elif attribute_type is dict and json.loads(parameter.parameter_value):
                parameter.parameter_value = json.loads(parameter.parameter_value)
            elif attribute_type == ExperimentStatus:
                parameter.parameter_value = ExperimentStatus(parameter.parameter_value)
            elif attribute_type == datetime:
                parameter.parameter_value = datetime.fromisoformat(
                    parameter.parameter_value
                )
            elif parameter.parameter_name == "solutions":
                parameter.parameter_value = json.loads(parameter.parameter_value)
            else:
                experiment_logger.debug(f"Unknown attribute type {attribute_type}")

            if hasattr(self, parameter.parameter_name):  # Check if the attribute exists
                setattr(self, parameter.parameter_name, parameter.parameter_value)
            else:
                # If the attribute does not exist, add it to the object, this is
                # to avoid every experiment needing to have attributes of other experiments
                # Example: Edot experiments have edot_concentration, but not all experiments have this
                setattr(
                    self.__class__, parameter.parameter_name, parameter.parameter_value
                )

    def increment_steps(self):
        self.steps += 1

    def declare_step(self, step: str, status: ExperimentStatus) -> str:
        """Handle setting the status"""
        global_logger.info("%d. %s", self.steps, step)
        self.increment_steps()
        self.set_status_and_save(status)


@dataclass(config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=False))
class EchemExperimentBase(ExperimentBase):
    """Define the data that is used to run an elechrochemical experiment.

    This is the base class for all echem experiments.
    """

    experiment_type: int = 1  # echem generic
    ocp: int = 1  # Open Circuit Potential
    ca: int = 1  # Cyclic Amperometry
    cv: int = 1  # Cyclic Voltammetry
    baseline: int = 0  # Baseline

    flush_sol_name: str = ""  # Flush solution name
    flush_sol_vol: Union[int, float] = 0  # Flush solution volume
    flush_count: int = 3  # Flush solution concentration

    mix = 0  # Binary mix or dont mix
    mix_count: int = 0  # Number of times to mix
    mix_volume: int = 0  # Volume to mix

    rinse_sol_name: str = "rinse"  # Rinse solution name
    rinse_count: int = 4  # Default rinse count
    rinse_vol: int = 120  # Default rinse volume

    ca_sample_period: float = float(0.1)  # Deposition sample period
    ca_prestep_voltage: float = float(0.0)  # Pre-step voltage (V)
    ca_prestep_time_delay: float = float(0.0)  # Pre-step delay time (s)
    ca_step_1_voltage: float = float(
        -1.7
    )  # Step 1 voltage (V), deposition potential (V)
    ca_step_1_time: float = float(
        300.0
    )  # run time 300 seconds, deposition duration (s)
    ca_step_2_voltage: float = float(0.0)  # Step 2 voltage (V)
    ca_step_2_time: float = float(0.0)  # Step 2 time (s)
    ca_sample_rate: float = float(0.5)  # sample period (s)

    char_sol_name: str = ""  # Characterization solution name
    char_vol: int = 0  # Characterization solution volume
    char_concentration: float = 1.0  # Characterization solution concentration
    cv_sample_period: float = float(0.1)  # Characterization sample period
    cv_initial_voltage: float = float(0.0)  # initial voltage
    cv_first_anodic_peak: float = float(0.5)  # first anodic peak
    cv_second_anodic_peak: float = float(-0.2)  # second anodic peak
    cv_final_voltage: float = float(0.0)  # final voltage
    cv_step_size: float = float(0.01)  # step size
    cv_cycle_count: int = 3  # number of cycles
    cv_scan_rate_cycle_1: float = float(0.1)
    cv_scan_rate_cycle_2: float = cv_scan_rate_cycle_1
    cv_scan_rate_cycle_3: float = cv_scan_rate_cycle_1

    @property
    def cv_sample_rate(self):
        """CVstep / CVsr1"""
        return round(self.cv_step_size / self.cv_scan_rate_cycle_1, 4)

    def print_ca_parameters(self) -> str:
        """Print the CA parameters"""
        if self.ca:
            return f"""
        CA Parameters
            Pre-step Voltage: {self.ca_prestep_voltage}
            Pre-step Time Delay: {self.ca_prestep_time_delay}
            Step 1 Voltage: {self.ca_step_1_voltage}
            Step 1 Time: {self.ca_step_1_time}
            Step 2 Voltage: {self.ca_step_2_voltage}
            Step 2 Time: {self.ca_step_2_time}
            CA Sample Rate: {self.ca_sample_rate}
    """
        else:
            return """
        CA Not selected
    """

    def print_cv_parameters(self) -> str:
        """Print the CV parameters"""
        if self.cv:
            return f"""
        CV Parameters
            CV: {bool(self.cv)}
            CV Baseline: {bool(self.baseline)}
            Sample Period: {self.cv_sample_period}
            Initial Voltage (CVvi): {self.cv_initial_voltage}
            First Anodic Peak (CVap1): {self.cv_first_anodic_peak}
            Second Anodic Peak (CVap2): {self.cv_second_anodic_peak}
            Final Voltage (CVvf): {self.cv_final_voltage}
            Step Size (CVstep): {self.cv_step_size}
            Cycle Count: {self.cv_cycle_count}
            Scan Rate Cycle 1 (CVsr1): {self.cv_scan_rate_cycle_1}
            Scan Rate Cycle 2 (CVsr2): {self.cv_scan_rate_cycle_2}
            Scan Rate Cycle 3 (CVsr3): {self.cv_scan_rate_cycle_3}
            CV Sample Rate: {self.cv_sample_rate}
    """
        else:
            return """
        CV not selected
"""

    def print_all_experiment_parameters(self) -> str:
        """Print the experiment parameters"""
        return f"""
{self.experiment_name} 
        Plate #: {self.plate_id}
        Experiment ID: {self.experiment_id}
        Well ID: {self.well_id}
        Status: {self.status.value}
        Priority: {self.priority}
        Solutions: {self.solutions}
        Filename: {self.filename}

        Echem Parameters
            Run Open Circuit Potential: {bool(self.ocp)}
            Run Cyclic Amperometry: {bool(self.ca)}
            Run Cyclic Voltammetry: {bool(self.cv)}
            Run CV Baseline: {bool(self.baseline)}
            Flush Solution Name: {self.flush_sol_name}
            Flush Solution Volume: {self.flush_sol_vol}
            Mix: {bool(self.mix)}
            Mix Count: {self.mix_count}
            Mix Volume: {self.mix_volume}
            Rinse Count: {self.rinse_count}
            Rinse Volume: {self.rinse_vol}

        {self.print_ca_parameters()}

        {self.print_cv_parameters()}
    """


def _select_next_experiment_id() -> int:
    """Determines the next experiment id by checking the experiment table"""

    with SessionLocal() as session:
        result = (
            session.query(Experiments.experiment_id)
            .order_by(Experiments.experiment_id.desc())
            .first()
        )
    if result in [None, []]:
        return 10000000
    return result[0] + 1


def select_experiment_information(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment information from the experiments table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment information.
    """

    with SessionLocal() as session:
        result = (
            session.query(Experiments)
            .filter(Experiments.experiment_id == experiment_id)
            .first()
        )

    if result is None:
        return None
    else:
        # With the project_id known to determine the experiment type
        # object type

        experiment = EchemExperimentBase()
        experiment.experiment_id = experiment_id
        experiment.project_id = result.project_id
        experiment.project_campaign_id = result.project_campaign_id
        experiment.plate_type_number = result.well_type
        experiment.protocol_id = result.protocol_id
        experiment.priority = result.priority
        experiment.filename = result.filename
        return experiment


def _select_experiment_parameters(experiment_id) -> list:
    """
    Selects the experiment parameters from the experiment_parameters table.
    If an experiment_object is provided, the parameters are added to the object.

    Args:
        experiment_to_select (Union[int, EchemExperimentBase]): The experiment ID or object.

    Returns:
        EchemExperimentBase: The experiment parameters.
    """
    with SessionLocal() as session:
        result = (
            session.query(ExperimentParameters)
            .filter(ExperimentParameters.experiment_id == experiment_id)
            .all()
        )
    values = []
    for row in result:
        values.append(row)

    return values


def _select_specific_parameter(experiment_id: int, parameter_name: str):
    """
    Select a specific parameter from the experiment_parameters table.

    Args:
        experiment_id (int): The experiment ID.
        parameter_name (str): The parameter name.

    Returns:
        any: The parameter value.
    """

    with SessionLocal() as session:
        result = (
            session.query(ExperimentParameters.parameter_value)
            .filter(ExperimentParameters.experiment_id == experiment_id)
            .filter(ExperimentParameters.parameter_name == parameter_name)
            .all()
        )

    if not result:
        return None
    return result[0][0]


def _select_experiment_status(experiment_id: int) -> str:
    """
    Select the status of an experiment from the well_hx table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        str: The status of the experiment.
    """

    with SessionLocal() as session:
        result = (
            session.query(ExperimentStatusView.status)
            .filter(ExperimentStatusView.experiment_id == experiment_id)
            .all()
        )

    if result == []:
        return ValueError("No experiment found with that ID")
    return result[0][0]


def _select_complete_experiment_information(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment information and parameters from the experiments and experiment_parameters tables.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment information and parameters.
    """

    experiment = select_experiment_information(experiment_id)
    if experiment is None:
        return None

    params = _select_experiment_parameters(experiment_id)
    experiment.map_parameter_list_to_experiment(params)
    if experiment is None:
        return None

    return experiment


def _insert_experiment(experiment: ExperimentBase) -> None:
    """
    Insert an experiment into the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    _insert_experiments([experiment])


def _insert_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Insert a list of experiments into the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.experiment_id,
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.plate_type_number,
                experiment.protocol_id,
                experiment.pin,
                experiment.experiment_type,
                experiment.jira_issue_key,
                experiment.priority,
                experiment.process_type,
                experiment.filename,
                datetime.now().isoformat(timespec="seconds"),
            )
        )

    with SessionLocal() as session:
        for parameter in parameters:
            session.add(
                Experiments(
                    experiment_id=parameter[0],
                    project_id=parameter[1],
                    project_campaign_id=parameter[2],
                    well_type=parameter[3],
                    protocol_id=parameter[4],
                    pin=parameter[5],
                    experiment_type=parameter[6],
                    jira_issue_key=parameter[7],
                    priority=parameter[8],
                    process_type=parameter[9],
                    filename=parameter[10],
                    created=datetime.strptime(parameter[11], "%Y-%m-%dT%H:%M:%S"),
                )
            )
        session.commit()


def _insert_experiment_parameters(experiment: ExperimentBase) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    _insert_experiments_parameters([experiment])


def _insert_experiments_parameters(experiments: List[ExperimentBase]) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters_to_insert = []  # this will be a list of tuples of the parameters to insert
    for experiment in experiments:
        experiment_parameters: list[ExperimentParameterRecord] = (
            experiment.generate_parameter_list()
        )
        for parameter in experiment_parameters:
            parameters_to_insert.append(
                (
                    experiment.experiment_id,
                    parameter.parameter_name,
                    (
                        json.dumps(parameter.parameter_value, default=str)
                        if isinstance(parameter.parameter_value, dict)
                        else parameter.parameter_value
                    ),
                    datetime.now().isoformat(timespec="seconds"),
                )
            )

    with SessionLocal() as session:
        for parameter in parameters_to_insert:
            session.add(
                ExperimentParameters(
                    experiment_id=parameter[0],
                    parameter_name=parameter[1],
                    parameter_value=parameter[2],
                    created=datetime.strptime(parameter[3], "%Y-%m-%dT%H:%M:%S"),
                )
            )
        session.commit()


def _update_experiment(experiment: ExperimentBase) -> None:
    """
    Update an experiment in the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to update.
    """
    _update_experiments([experiment])


def _update_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Update a list of experiments in the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to update.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.plate_type_number,
                experiment.protocol_id,
                experiment.pin,
                experiment.experiment_type,
                experiment.jira_issue_key,
                experiment.priority,
                experiment.process_type,
                experiment.filename,
                experiment.experiment_id,
            )
        )

    with SessionLocal() as session:
        for parameter in parameters:
            session.query(Experiments).filter(
                Experiments.experiment_id == parameter[10]
            ).update(
                {
                    Experiments.project_id: parameter[0],
                    Experiments.project_campaign_id: parameter[1],
                    Experiments.well_type: parameter[2],
                    Experiments.protocol_id: parameter[3],
                    Experiments.pin: parameter[4],
                    Experiments.experiment_type: parameter[5],
                    Experiments.jira_issue_key: parameter[6],
                    Experiments.priority: parameter[7],
                    Experiments.process_type: parameter[8],
                    Experiments.filename: parameter[9],
                }
            )
        session.commit()


def _update_experiment_status(
    experiment: Union[ExperimentBase, int],
    status: ExperimentStatus = None,
    status_date: datetime = None,
) -> None:
    """
    Update the status of an experiment in the experiments table.

    When provided with an int, the experiment_id is the int, and the status and
    status_date are the other two arguments.
    If no status is provided, the function will not make assumptions and will do nothing.

    When provided with an ExperimentBase object, the object's attributes will be
    used to update the status.
    If an object is provided along with a status and status date, the object's
    attributes will be updated with the status and status date.

    Args:
        experiment_id (int): The experiment ID.
        status (ExperimentStatus): The status to update to.
    """
    # Handel the case where the experiment is passed as an object or an int
    # If it is an int, then the experiment_id is the int, and the status and the
    # status_date are the other two arguments
    # If it is an object, then use the experimentbase object for the data
    if isinstance(experiment, int):
        experiment_id = experiment
        if status is None:
            return
        if status_date is None:
            status_date = datetime.now().isoformat(timespec="seconds")

        experiment_info = select_experiment_information(experiment_id)
        project_id = experiment_info.project_id
        well_id = experiment_info.well_id

    else:
        experiment_id = experiment.experiment_id
        if status is not None:
            experiment.set_status(status)
        else:
            status = experiment.status
        if status_date is not None:
            experiment.status_date = status_date
        else:
            status_date = experiment.status_date
        project_id = experiment.project_id
        well_id = experiment.well_id

    with SessionLocal() as session:
        subquery = (
            session.query(Wellplates.id)
            .filter(Wellplates.current == 1)
            .scalar_subquery()
        )
        session.query(WellModel).filter(WellModel.well_id == well_id).filter(
            WellModel.plate_id == subquery
        ).update(
            {
                WellModel.status: status.value,
                WellModel.status_date: status_date,
                WellModel.experiment_id: experiment_id,
                WellModel.project_id: project_id,
            }
        )
        session.commit()


def _update_experiments_statuses(
    experiments: List[ExperimentBase],
    exp_status: ExperimentStatus,
    status_date: datetime = None,
) -> None:
    """
    Set the status of a list of experiments in the well_hx table.

    Args:
        experiments (List[ExperimentBase]): The experiments to set the status for.
        status (ExperimentStatus): The status to set for the experiments.
        status_date (datetime): The status date to set for the experiments.
    """
    if status_date is None:
        status_date = datetime.now().isoformat(timespec="seconds")

    for experiment in experiments:
        experiment.set_status(exp_status)

    parameters = [
        (
            exp_status.value,
            status_date,
            experiment.experiment_id,
            experiment.project_id,
            experiment.well_id,
        )
        for experiment in experiments
    ]
    # execute_sql_command_no_return(
    #     """
    #     UPDATE well_hx
    #     SET status = ?,
    #     status_date = ?,
    #     experiment_id = ?,
    #     project_id = ?
    #     WHERE well_id = ?
    #     AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
    #     """,
    #     parameters,
    # )

    with SessionLocal() as session:
        for parameter in parameters:
            session.query(WellModel).filter(WellModel.well_id == parameter[4]).filter(
                WellModel.plate_id
                == session.query(Wellplates.id).filter(Wellplates.current == 1)
            ).update(
                {
                    WellModel.status: parameter[0],
                    WellModel.status_date: parameter[1],
                    WellModel.experiment_id: parameter[2],
                    WellModel.project_id: parameter[3],
                }
            )
        session.commit()


def _get_all_type_hints(cls):
    """Get all type hints for a class"""
    hints = {}
    for base in reversed(cls.__mro__):
        hints.update(get_type_hints(base))
    return hints


def parse_experiment(json_string: str) -> ExperimentBase:
    """Parse an experiment from a json string"""
    if isinstance(json_string, str):
        parsed_json = json.loads(json_string)
        if "ocp" in parsed_json:
            return RootModel[EchemExperimentBase].model_validate_json(json_string).root
    return RootModel[ExperimentBase].model_validate_json(json_string).root


# def serialize_experiment(experiment: (Experiment,ExperimentBase)) -> str:
#     '''Serialize an experiment to a json string'''
#     if isinstance(experiment, Experiment):
#         return RootModel[Experiment](experiment).model_dump_json(indent=4)


def serialize_experiment(experiment: tuple[ExperimentBase, EchemExperimentBase]) -> str:
    """Given an experiment, determine the type and then pass back the serialized json form"""

    if isinstance(experiment, EchemExperimentBase):
        return RootModel[EchemExperimentBase](experiment).model_dump_json(indent=4)
    if isinstance(experiment, ExperimentBase):
        return RootModel[ExperimentBase](experiment).model_dump_json(indent=4)
    return None
