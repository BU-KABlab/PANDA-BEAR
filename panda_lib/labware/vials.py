import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict, Union

from sqlalchemy.orm import Session, sessionmaker

from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.utilities import Coordinates, directory_picker, file_picker
from shared_utilities.log_tools import setup_default_logger

from .errors import OverDraftException, OverFillException  # Custom exceptions
from .schemas import VialReadModel, VialWriteModel  # Pydantic models
from .services import VialService

vial_logger = setup_default_logger("vial_logger")


# Define TypedDict for Vial kwargs
class VialKwargs(TypedDict, total=False):
    category: int
    height: float
    radius: float
    volume: float
    capacity: float
    contamination: int
    dead_volume: float
    contents: Dict[str, float]
    viscosity_cp: float
    concentration: float
    density: float
    coordinates: Dict[str, float]
    name: str
    base_thickness: float


class Vial:
    def __init__(
        self,
        position: str,
        session_maker: sessionmaker = SessionLocal,
        create_new: bool = False,
        **kwargs: VialKwargs,
    ):
        """
        Initializes a Vial instance for managing vial business logic.

        Args:
            position (str): Position of the vial.
            session (Session): SQLAlchemy session for database interactions.
            create_new (bool): Whether to create a new vial in the database.
            **kwargs: Additional attributes for creating a new vial.
        """
        self.position = position
        self.session_maker = session_maker
        self.service = VialService(self.session_maker)
        self.vial_data: Optional[VialReadModel] = None

        if create_new:
            self.create_new_vial(**kwargs)
        else:
            self.load_vial()

    @property
    def x(self) -> float:
        """Returns the x-coordinate of the vial."""
        return self.coordinates.x

    @property
    def y(self) -> float:
        """Returns the y-coordinate of the vial."""
        return self.coordinates.y

    @property
    def z(self) -> float:
        """Returns the z-coordinate of the vial."""
        return self.coordinates.z

    @property
    def top(self) -> float:
        """Returns the top of the vial."""
        return self.vial_data.top

    @property
    def bottom(self) -> float:
        """Returns the bottom of the vial."""
        return self.vial_data.bottom

    @property
    def volume(self) -> float:
        """Returns the current volume of the vial."""
        return self.vial_data.volume

    @property
    def contents(self) -> Dict[str, float]:
        """Returns the contents of the vial."""
        return self.vial_data.contents

    @property
    def viscosity_cp(self) -> float:
        """Returns the viscosity of the vial."""
        return self.vial_data.viscosity_cp

    @property
    def category(self) -> int:
        """Returns the category of the vial."""
        return self.vial_data.category

    @property
    def name(self) -> str:
        """Returns the name of the vial."""
        return self.vial_data.name

    @property
    def capacity(self) -> float:
        """Returns the capacity of the vial."""
        return self.vial_data.capacity

    @property
    def contamination(self) -> int:
        """Returns the contamination count of the vial."""
        return self.vial_data.contamination

    @property
    def coordinates(self) -> Coordinates:
        """Returns the coordinates of the vial."""
        return Coordinates(**self.vial_data.coordinates)

    @property
    def density(self) -> float:
        """Returns the density of the vial."""
        return self.vial_data.density

    @property
    def concentration(self) -> float:
        """Returns the concentration of the vial."""
        return self.vial_data.concentration

    @property
    def withdrawal_height(self) -> float:
        """Returns the height of the vial from which contents are withdrawn."""
        height = self.vial_data.volume_height - 1
        dead_height = self.bottom + self.vial_data.dead_volume / (
            3.14 * self.vial_data.radius**2
        )
        if height < dead_height:
            return dead_height
        else:
            return height

    def create_new_vial(self, **kwargs: VialKwargs):
        """Creates a new vial in the database, and loads it back."""
        new_vial = VialWriteModel(position=self.position, **kwargs)
        self.vial_data = VialWriteModel.model_validate(
            self.service.create_vial(new_vial)
        )
        self.load_vial()

    def load_vial(self):
        """Loads an existing vial from the database."""
        self.vial_data = self.service.get_vial(self.position)

    def save(self):
        """Updates the database with the current state of the vial."""
        self.service.update_vial(self.position, self.vial_data.model_dump())

    def add_contents(self, from_vessel: Dict[str, float], volume: float):
        """
        Adds contents to the vial.

        Args:
            from_vessel (Dict[str, float]): Contents to be added.
            volume (float): Volume to add.

        Raises:
            OverFillException: If the volume exceeds the vial's capacity.
        """
        if self.vial_data.category == 0:
            raise ValueError("Stock vials cannot have contents added to them.")
        else:
            if self.vial_data.volume + volume > self.vial_data.capacity:
                raise OverFillException(
                    self.vial_data.name,
                    self.vial_data.volume,
                    volume,
                    self.vial_data.capacity,
                )

            for key, val in from_vessel.items():
                if key in self.vial_data.contents:
                    self.vial_data.contents[key] += val
                else:
                    self.vial_data.contents[key] = val

            self.vial_data.volume += volume

        self.save()

    def remove_contents(self, volume: float) -> Dict[str, float]:
        """
        Removes contents from the vial.

        Args:
            volume (float): Volume to remove.

        Returns:
            Dict[str, float]: The removed contents.

        Raises:
            OverDraftException: If the volume to remove exceeds the vial's current volume.
        """
        if self.vial_data.volume - volume < 0:
            raise OverDraftException(
                self.vial_data.name,
                self.vial_data.volume,
                -volume,
                self.vial_data.capacity,
            )

        current_content_ratios = {
            key: value / sum(self.vial_data.contents.values())
            for key, value in self.vial_data.contents.items()
        }

        removed_contents = {}
        for key in self.vial_data.contents:
            removed_volume = round(volume * current_content_ratios[key], 6)
            self.vial_data.contents[key] -= removed_volume
            removed_contents[key] = removed_volume

        self.vial_data.volume -= volume
        self.save()

        return removed_contents

    def reset_vial(self):
        """Resets the vial to its default state."""
        self.vial_data.volume = (
            self.vial_data.capacity if self.vial_data.category == 0 else 0
        )
        self.vial_data.contents = (
            {}
            if self.vial_data.category == 1
            else {next(iter(self.vial_data.contents)): self.vial_data.capacity}
        )
        self.save()
        self.vial_data.contamination = 0
        self.save()

    def __repr__(self):
        return f"<Vial(position={self.position}, volume={self.vial_data.volume}, contents={self.vial_data.contents}. top={self.vial_data.top}, bottom={self.vial_data.bottom})>"


class StockVial(Vial):
    def add_contents(self, from_vessel: Dict[str, float], volume: float):
        """
        Adds contents to the vial.

        Args:
            from_vessel (Dict[str, float]): Contents to be added.
            volume (float): Volume to add.

        Raises:
            OverFillException: If the volume exceeds the vial's capacity.
        """
        raise ValueError("Stock vials cannot have contents added to them.")


class WasteVial(Vial):
    pass


def read_vials(
    vial_group: Optional[str] = None,
    session: sessionmaker = SessionLocal,
) -> Tuple[List[StockVial], List[WasteVial]]:
    """
    Read in the virtual vials from the json file
    """
    # groups = {"stock": 0, "waste": 1}
    # Get the vial information from the vials table in the db
    active_vials: List[VialReadModel] = VialService(
        db_session_maker=session
    ).list_active_vials()

    list_of_stock_solutions = []
    list_of_waste_solutions = []

    for vial in active_vials:
        if vial.category == 0:
            read_vial = StockVial(
                **vial.model_dump(), session_maker=session, create_new=False
            )
            list_of_stock_solutions.append(read_vial)
        elif vial.category == 1:
            read_vial = WasteVial(
                **vial.model_dump(), session_maker=session, create_new=False
            )
            list_of_waste_solutions.append(read_vial)
    if vial_group == "stock":
        return list_of_stock_solutions, None
    elif vial_group == "waste":
        return list_of_waste_solutions, None
    else:
        return list_of_stock_solutions, list_of_waste_solutions

    # for items in vial_parameters:
    #     if items["name"] is not None:
    #         if items["category"] == 0:  # Stock vial
    #             read_vial = StockVial(**items)
    #             list_of_stock_solutions.append(read_vial)
    #         elif items["category"] == 1:  # Waste vial
    #             read_vial = WasteVial(**items)
    #             list_of_waste_solutions.append(read_vial)
    # return list_of_stock_solutions, list_of_waste_solutions


def reset_vials(
    categoty: Union[str, int],
    session: Session = SessionLocal(),
) -> List[Vial]:
    """
    Reset the active vials in the database
    """

    if categoty == "stock" or categoty == 0:
        active_vials, _ = read_vials(session)
    elif categoty == "waste" or categoty == 1:
        _, active_vials = read_vials(session)

    for vial in active_vials:
        vial: Vial
        vial.reset_vial()

    return active_vials


def delete_vial_position_and_hx_from_db(
    position: str, session: Session = SessionLocal
) -> None:
    """Delete the vial position and hx from the db"""
    try:
        VialService(db_session_maker=session).delete_vial(position)

    except Exception as e:
        vial_logger.error(
            "Error occurred while deleting vial position and hx from the db: %s", e
        )
        vial_logger.error("Continuing....")
        vial_logger.exception(e)


def input_new_vial_values(vialgroup: str) -> None:
    """For user inputting the new vial values for the state file"""

    vials = read_vials(vialgroup)[0]
    vials = sorted(vials, key=lambda x: x.position)
    vial_list = []
    vial_lines = []
    ## Print the current vials and their values
    print("Current vials:")

    max_lengths = [10, 20, 20, 15, 15, 15, 15]  # Initialize max lengths for each column
    for vial in vials:
        vial: Vial
        vial_list.append(vial)
        # if vial.contents is None:
        #     vial_entry.contents = {}
        # if vial.name is None:
        #     # All parameters are blank except for position
        #     vial_entry.name = "--"
        #     vial_entry.vial_data.contents = "--"
        #     vial_entry.vial_data.density = "--"
        #     vial_entry.vial_data.volume = "--"
        #     vial_entry.vial_data.capacity = "--"
        #     vial_entry.vial_data.contamination = "--"

        values = [
            vial.vial_data.position,
            vial.vial_data.name,
            str(vial.vial_data.contents),
            vial.vial_data.density,
            vial.vial_data.volume,
            vial.vial_data.capacity,
            vial.vial_data.contamination,
        ]
        max_lengths = [
            max(max_lengths[i], len(str(values[i]))) for i in range(len(values))
        ]  # Update max lengths

        vial_lines.append(
            f"{values[0]:<{max_lengths[0]}} {values[1]:<{max_lengths[1]}} {values[2]:<{max_lengths[2]}} {values[3]:<{max_lengths[3]}} {values[4]:<{max_lengths[4]}} {values[5]:<{max_lengths[5]}} {values[6]:<{max_lengths[6]}}"
        )

    header_string = f"{'Position':<{max_lengths[0]}} {'Name':<{max_lengths[1]}} {'Contents':<{max_lengths[2]}} {'Density':<{max_lengths[3]}} {'Volume':<{max_lengths[4]}} {'Capacity':<{max_lengths[5]}} {'Contamination':<{max_lengths[6]}}"
    print(header_string)
    for line in vial_lines:
        print(line)

    while True:
        choice = input(
            "Which vial would you like to change? Enter the position of the vial or 'q' if finished: "
        )
        if choice == "q":
            break
        for vial in vials:
            vial: Vial
            if vial.position == choice:
                print(
                    "Please enter the new values for the vial, if you leave any blank the value will not be changed"
                )
                print(f"\nVial {vial.position}:")
                new_name = input(
                    f"Enter the new name of the vial (Current name is {vial.name}): "
                )
                if new_name != "":
                    vial.vial_data.name = new_name
                if vial.category == 0:  # Stock vial
                    current_key = next(iter(vial.contents.keys()))
                    new_key = input(
                        f"Enter the new contents of the vial (Currently is {current_key}): "
                    )
                    if new_key != "":
                        vial.vial_data.contents = {new_key: vial.contents[current_key]}
                new_density = input(
                    f"Enter the new density of the vial (Current density is {vial.vial_data.density}): "
                )
                if new_density != "":
                    vial.vial_data.density = float(new_density)
                new_volume = input(
                    f"Enter the new volume of the vial (Current volume is {vial.volume}): "
                )
                if new_volume != "":
                    vial.vial_data.volume = float(new_volume)
                new_capacity = input(
                    f"Enter the new capacity of the vial (Current capacity is {vial.capacity}): "
                )
                if new_capacity != "":
                    vial.vial_data.capacity = float(new_capacity)
                new_contamination = input(
                    f"Enter the new contamination of the vial (Current contamination is {vial.contamination}): "
                )
                if new_contamination != "":
                    try:
                        vial.contamination = int(new_contamination)
                    except ValueError:
                        print("Invalid value for contamination. Should be integer")
                        continue

                vial.save()
                # print("\r" + " " * 100 + "\r", end="")  # Clear the previous table
                print("\nCurrent vials:")
                print(
                    f"{'Position':<10} {'Name':<20} {'Contents':<20} {'Density':<15} {'Volume':<15} {'Capacity':<15} {'Contamination':<15}"
                )

                for vial in vials:
                    vial: Vial
                    # if vial.contents is None:
                    #     vial.contents = {}
                    # if vial.name is None:
                    #     # All parameters are blank except for position
                    #     vial.vial_data.name = ""
                    #     vial.vial_data.contents = ""
                    #     vial.vial_data.density = ""
                    #     vial.vial_data.volume = ""
                    #     vial.vial_data.capacity = ""
                    #     vial.vial_data.contamination = ""

                    # contents_str = str(
                    #     vial.vial_data.contents
                    # )  # Convert contents dictionary to string
                    print(
                        f"{vial.position:<10} {vial.name:<20} {str(vial.vial_data.contents):<20} {vial.vial_data.density:<15} {vial.volume:<15} {vial.capacity:<15} {vial.contamination:<15}"
                    )
                break
        else:
            print("Invalid vial position")
            continue


def generate_template_vial_csv_file() -> None:
    """
    Generate a template vial csv file that can be filled with
    multiple vials and their values
    """
    filename = "vials.csv"

    # Prompt the user to idenitfy the directory to save the file
    directory = directory_picker()

    filename = Path(directory) / Path(filename)  # Convert to a Path object
    stockvials, wastevials = read_vials()
    with open(filename, "w", encoding="UTF-8", newline="") as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(
            [
                "id",
                "position",
                "category",
                "name",
                "contents",
                "viscosity_cp",
                "concentration",
                "density",
                "height",
                "radius",
                "volume",
                "capacity",
                "contamination",
                "coordinates",
                "base_thickness",
                "dead_volume",
                "volume_height",
                "bottom",
                "top",
                "updated",
                "active",
            ]
        )
        for vial in stockvials + wastevials:
            vial: Vial
            csv_writer.writerow(
                [
                    vial.vial_data.id,
                    vial.vial_data.position,
                    vial.vial_data.category,
                    vial.vial_data.name,
                    json.dumps(vial.vial_data.contents),
                    vial.vial_data.viscosity_cp,
                    vial.vial_data.concentration,
                    vial.vial_data.density,
                    vial.vial_data.height,
                    vial.vial_data.radius,
                    vial.vial_data.volume,
                    vial.vial_data.capacity,
                    vial.vial_data.contamination,
                    json.dumps(vial.vial_data.coordinates),
                    vial.vial_data.base_thickness,
                    vial.vial_data.dead_volume,
                    vial.vial_data.volume_height,
                    vial.vial_data.bottom,
                    vial.vial_data.top,
                    vial.vial_data.updated,
                    vial.vial_data.active,
                ]
            )

    print(f"Template vial csv file saved as {filename}")


def import_vial_csv_file(filename: str = None) -> None:
    """
    Import the vial csv file and add the vials to the db
    """
    if not filename:
        filename = file_picker("csv")
    if not filename:
        return
    with open(filename, "r", encoding="UTF-8") as file:
        csv_reader = csv.DictReader(file)
        vial_parameters = []
        for row in csv_reader:
            vial_parameters.append(row)

    for each_vial in vial_parameters:
        try:
            vial = Vial(
                position=each_vial["position"],
                session_maker=SessionLocal,
                create_new=True,
                category=int(each_vial["category"]),
                name=each_vial["name"],
                contents=json.loads(each_vial["contents"]),
                viscosity_cp=float(each_vial["viscosity_cp"]),
                concentration=float(each_vial["concentration"]),
                density=float(each_vial["density"]),
                coordinates=json.loads(each_vial["coordinates"]),
                height=float(each_vial["height"]),
                radius=float(each_vial["radius"]),
                volume=float(each_vial["volume"]),
                capacity=float(each_vial["capacity"]),
                contamination=int(each_vial["contamination"]),
                dead_volume=float(each_vial["dead_volume"]),
            )

            vial_logger.info("Vial %s imported successfully", vial.position)
        except Exception as e:
            vial_logger.error(
                "Error occurred while importing vial %s: %s", each_vial["position"], e
            )
            vial_logger.error("Continuing....")
            vial_logger.exception(e)
