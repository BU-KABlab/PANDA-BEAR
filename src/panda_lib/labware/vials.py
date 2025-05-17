import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from sqlalchemy.orm import sessionmaker

from panda_lib.types import VialKwargs
from panda_lib.utilities import Coordinates, directory_picker, file_picker
from panda_shared.config.config_tools import read_config_value
from panda_shared.db_setup import SessionLocal
from panda_shared.log_tools import setup_default_logger

from .errors import OverDraftException, OverFillException  # Custom exceptions
from .schemas import VialReadModel, VialWriteModel  # Pydantic models
from .services import VialService

vial_logger = setup_default_logger("vial_logger")


class Vial:
    def __init__(
        self,
        position: Optional[str] = None,
        session_maker: sessionmaker = SessionLocal,
        create_new: bool = False,
        vial_name: Optional[str] = None,
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
        if position:
            self.position: str = position
        self.session_maker = session_maker
        self.service = VialService(self.session_maker)
        self.vial_data: VialReadModel
        self._vial_name = vial_name

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
    def top(self) -> Optional[float]:
        """Returns the top of the vial."""
        return self.vial_data.top

    @property
    def bottom(self) -> Optional[float]:
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
        height = self.vial_data.volume_height - 2
        bottom = self.bottom if self.bottom else 0
        if self.vial_data.dead_volume == 0:
            dead_height = bottom
        else:
            dead_height = bottom + self.vial_data.dead_volume / (
                3.14 * self.vial_data.radius**2
            )
        if height < dead_height:
            return dead_height
        else:
            return height

    def create_new_vial(self, **kwargs: VialKwargs):
        """Creates a new vial in the database, and loads it back."""
        if not self.position:
            # Check if the kwargs contain a position
            if "position" in kwargs:
                self.position = kwargs["position"]
            else:
                raise ValueError("Position must be provided to create a new vial.")
        new_vial = VialWriteModel(
            position=self.position,
            category=kwargs.get("category", 0),
            height=kwargs.get("height", 57.0),
            radius=kwargs.get("radius", 13.5),
            volume=kwargs.get("volume", 20000.0),
            capacity=kwargs.get("capacity", 20000.0),
            contamination=kwargs.get("contamination", 0),
            dead_volume=kwargs.get("dead_volume", 1000.0),
            contents=kwargs.get("contents", {}),
            viscosity_cp=kwargs.get("viscosity_cp", 0.0),
            concentration=kwargs.get("concentration", 0.0),
            density=kwargs.get("density", 1.0),
            coordinates=kwargs.get("coordinates", {"x": 0.0, "y": 0.0, "z": 0.0}),
            name=kwargs.get("name", self._vial_name),
            base_thickness=kwargs.get("base_thickness", 1.0),
            panda_unit_id=read_config_value("PANDA", "unit_id", 1),
        )
        self.vial_data = VialWriteModel.model_validate(
            self.service.create_vial(new_vial)
        )  # type: ignore
        time.sleep(0.5)  # Wait for the vial to be created in the database
        self.load_vial()

    def load_vial(self):
        """Loads an existing vial from the database."""
        if self._vial_name:
            self.vial_data = self.service.get_vial(name=self._vial_name)
        else:
            self.vial_data = self.service.get_vial(position=self.position)

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

    def get_xyz(self) -> Tuple[float, float, float]:
        """
        Returns the x, y, z coordinates of the vial.

        Returns:
            Tuple[float, float, float]: The x, y, z coordinates of the vial.
        """
        return self.x, self.y, self.z

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


def read_vial(
    name: Optional[str] = None,
    position: Optional[str] = None,
    session: sessionmaker = SessionLocal,
) -> Vial:
    """
    Read a vial from the database, either by name or position
    """
    if name:
        if position:
            vial = Vial(
                position=position,
                vial_name=name,
                session_maker=session,
                create_new=False,
            )
        else:
            vial = Vial(vial_name=name, session_maker=session, create_new=False)
    elif position:
        vial = Vial(position=position, session_maker=session, create_new=False)
        if name:
            assert vial.vial_data.name == name
    else:
        raise ValueError("Either name or position must be provided")

    return vial


def read_vials(
    vial_group: Optional[str] = None,
    session: sessionmaker = SessionLocal,
) -> Union[Tuple[List[StockVial], List[WasteVial]], Tuple[List[Vial], None]]:
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


def reset_vials(
    categoty: Union[str, int],
    session: sessionmaker = SessionLocal,
) -> Sequence[Vial]:
    """
    Reset the active vials in the database
    """
    active_vials: Sequence[Vial]
    if categoty == "stock" or categoty == 0:
        active_vials, _ = read_vials("stock", session=session)
    elif categoty == "waste" or categoty == 1:
        active_vials, _ = read_vials("waste", session=session)

    for vial in active_vials:
        vial: Vial
        vial.reset_vial()

    return active_vials


def delete_vial_position_and_hx_from_db(
    position: str, session: sessionmaker = SessionLocal
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


# def input_new_vial_values(vialgroup: str) -> None:
#     """For user inputting the new vial values for the state file"""

#     vials = read_vials(vialgroup)[0]
#     vials = sorted(vials, key=lambda x: x.vial_data.position)
#     vial_list = []
#     vial_lines = []
#     ## Print the current vials and their values
#     print("Current vials:")

#     max_lengths = [10, 20, 20, 15, 15, 15, 15]  # Initialize max lengths for each column
#     for vial in vials:
#         vial: Vial
#         vial_list.append(vial)
#         values = [
#             vial.vial_data.position,
#             vial.vial_data.name,
#             str(vial.vial_data.contents),
#             vial.vial_data.density,
#             vial.vial_data.volume,
#             vial.vial_data.capacity,
#             vial.vial_data.contamination,
#         ]
#         max_lengths = [
#             max(max_lengths[i], len(str(values[i]))) for i in range(len(values))
#         ]  # Update max lengths

#     for vial in vial_list:
#         values = [
#             vial.vial_data.position,
#             vial.vial_data.name,
#             str(vial.vial_data.contents),
#             vial.vial_data.density,
#             vial.vial_data.volume,
#             vial.vial_data.capacity,
#             vial.vial_data.contamination,
#         ]
#         vial_lines.append(
#             f"{values[0]:<{max_lengths[0]}} {values[1]:<{max_lengths[1]}} {values[2]:<{max_lengths[2]}} {values[3]:<{max_lengths[3]}} {values[4]:<{max_lengths[4]}} {values[5]:<{max_lengths[5]}} {values[6]:<{max_lengths[6]}}"
#         )


#     header_string = f"{'Position':<{max_lengths[0]}} {'Name':<{max_lengths[1]}} {'Contents':<{max_lengths[2]}} {'Density':<{max_lengths[3]}} {'Volume':<{max_lengths[4]}} {'Capacity':<{max_lengths[5]}} {'Contamination':<{max_lengths[6]}}"
#     print(header_string)
#     for line in vial_lines:
#         print(line)
def enter_new_vial() -> Vial:
    """Function to enter a new vial into the database."""
    print(
        "You may enter a new vial using the default positions:\n\tS0, S1, S2, S3, S4, S5, S6, S7, S8\n\tW0, W1, W2, W3, W4, W5, W6, W7, W8"
    )

    while True:
        position = input("Enter the position of the new vial: ")
        if position == "q":
            return None

        # Validate position format
        if position == "":
            print("Position cannot be empty. Please enter a new position.")
            continue
        if position[0] not in ["S", "W"]:
            print("Position must start with S or W. Please enter a new position.")
            continue
        if not (position[1:].isdigit() and int(position[1:]) < 9):
            print("Position must end with a digit 0-8. Please enter a new position.")
            continue

        # Check if position already exists
        try:
            Vial(position=position, create_new=False)
            print(f"Vial {position} already exists. Please enter a new position.")
            continue
        except Exception:
            # Position doesn't exist, we can proceed
            pass

        print(f"Position {position} is valid. Please enter the values for the vial.")
        category = 0 if position[0] == "S" else 1
        name = input("Enter the name of the vial: ")

        # Get contents
        contents = input("Enter the contents of the vial (in json format): ")
        if contents == "":
            contents = "{}"
        try:
            contents = json.loads(contents)
        except json.JSONDecodeError:
            print("Invalid json format for contents. Please enter a valid json.")
            continue

        # Get remaining properties
        density = input("Enter the density of the vial: ") or "1.0"
        volume = input("Enter the volume of the vial: ") or "0.0"
        capacity = input("Enter the capacity of the vial: ") or "20000"
        contamination = 0

        coordinates = input(
            'Enter the coordinates of the bottom of the vial (in {"x":#,"y":#,"z":#} format): '
        )
        if coordinates == "":
            coordinates = {"x": 0.0, "y": 0.0, "z": -200.0}
        else:
            try:
                coordinates = json.loads(coordinates)
            except json.JSONDecodeError:
                print("Invalid json format for coordinates. Please enter a valid json.")
                continue

        base_thickness = input("Enter the base thickness of the vial: ") or "1.0"
        dead_volume = input("Enter the dead volume of the vial: ") or "0.0"
        active = 1

        try:
            vial = Vial(
                position=position,
                session_maker=SessionLocal,
                create_new=True,
                vial_name=name,
                category=category,
                contents=contents,
                density=float(density),
                volume=float(volume),
                capacity=float(capacity),
                contamination=contamination,
                coordinates=coordinates,
                base_thickness=float(base_thickness),
                dead_volume=float(dead_volume),
                active=active,
            )
            vial_logger.info("Vial %s created successfully", position)
            print(
                f"Vial {position} created successfully with the following values:\n"
                f"\tName: {name}\n"
                f"\tContents: {contents}\n"
                f"\tDensity: {density}\n"
                f"\tVolume: {volume}\n"
                f"\tCapacity: {capacity}\n"
                f"\tContamination: {contamination}\n"
                f"\tCoordinates: {coordinates}\n"
                f"\tBase thickness: {base_thickness}\n"
                f"\tDead volume: {dead_volume}"
            )
            return vial
        except Exception as e:
            vial_logger.error("Error occurred while creating vial %s: %s", position, e)
            vial_logger.error("Continuing....")
            vial_logger.exception(e)


def update_existing_vial(vials: List[Vial]) -> None:
    """Function to update an existing vial in the database."""
    if not vials:
        print("No existing vials found to update.")
        return

    while True:
        choice = input("Enter the position of the vial to update or 'q' to quit: ")
        if choice == "q":
            break

        for vial in vials:
            if vial.position == choice:
                print(
                    "Please enter the new values for the vial, if you leave any blank the value will not be changed"
                )
                print(f"\nUpdating Vial {vial.position}:")

                new_name = input(
                    f"Enter the new name of the vial (Current name is {vial.name}): "
                )
                if new_name != "":
                    vial.vial_data.name = new_name

                if vial.category == 0:  # Stock vial
                    current_key = next(iter(vial.contents.keys()))
                    new_key = input(
                        f"Enter the new contents name of the vial (Currently is {current_key}): "
                    )
                    if new_key != "":
                        # Replace the key in the contents dictionary with the new key but old value
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
                    if vial.vial_data.category == 0:  # Stock vial
                        # Get the key of the contents
                        key = next(iter(vial.vial_data.contents.keys()))
                        # Update the new volume in the contents dictionary
                        vial.vial_data.contents = {key: float(new_volume)}

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
                        vial.vial_data.contamination = int(new_contamination)
                    except ValueError:
                        print("Invalid value for contamination. Should be integer")
                        continue

                vial.save()
                print(f"Vial {vial.position} updated successfully.")
                break
        else:
            print("Invalid vial position")


def input_new_vial_values(vialgroup: str) -> None:
    """For user inputting the new vial values for the state file"""

    vials = read_vials(vialgroup)[0]
    vials = sorted(vials, key=lambda x: x.vial_data.position)

    ## Print the current vials and their values
    print("Current vials:")

    if vials:
        max_lengths = [
            10,
            20,
            20,
            15,
            15,
            15,
            15,
        ]  # Initialize max lengths for each column
        vial_list = []
        vial_lines = []

        for vial in vials:
            vial: Vial
            vial_list.append(vial)
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

        for vial in vial_list:
            values = [
                vial.vial_data.position,
                vial.vial_data.name,
                str(vial.vial_data.contents),
                vial.vial_data.density,
                vial.vial_data.volume,
                vial.vial_data.capacity,
                vial.vial_data.contamination,
            ]
            vial_lines.append(
                f"{values[0]:<{max_lengths[0]}} {values[1]:<{max_lengths[1]}} {values[2]:<{max_lengths[2]}} {values[3]:<{max_lengths[3]}} {values[4]:<{max_lengths[4]}} {values[5]:<{max_lengths[5]}} {values[6]:<{max_lengths[6]}}"
            )

        header_string = f"{'Position':<{max_lengths[0]}} {'Name':<{max_lengths[1]}} {'Contents':<{max_lengths[2]}} {'Density':<{max_lengths[3]}} {'Volume':<{max_lengths[4]}} {'Capacity':<{max_lengths[5]}} {'Contamination':<{max_lengths[6]}}"
        print(header_string)
        for line in vial_lines:
            print(line)
    else:
        print("No vials found in the database.")

    while True:
        if not vials:
            # No vials, go straight to entering a new one
            vial = enter_new_vial()
            if vial:
                vials.append(vial)
                print("Vial added. Enter another vial or 'q' to quit.")
            else:
                break
        else:
            # Ask if they want to enter a new vial or update existing
            choice = input(
                "Enter 'n' for new vial, 'u' to update existing vial, or 'q' to quit: "
            )
            if choice == "q":
                break
            elif choice == "n":
                vial = enter_new_vial()
                if vial:
                    vials.append(vial)
            elif choice == "u":
                update_existing_vial(vials)
            else:
                print("Invalid choice. Please enter 'n', 'u', or 'q'.")


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
                "active",
            ]
        )
        all_vials = (stockvials if stockvials else []) + (
            wastevials if wastevials else []
        )
        for vial in all_vials:
            vial: Vial
            csv_writer.writerow(
                [
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
                    vial.vial_data.active,
                ]
            )

    print(f"Template vial csv file saved as {filename}")


def import_vial_csv_file(filename: Optional[str] = None) -> None:
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

    # Data cleaning - remove rows with empty names or positions
    vial_parameters_clean = [
        vial for vial in vial_parameters if vial["name"] and vial["position"]
    ]

    for each in vial_parameters_clean:
        if (
            each["contents"] is None
            or each["contents"] == ""
            or each["contents"] == "none"
        ):
            each["contents"] = "{}"

    for each_vial in vial_parameters_clean:
        try:
            vkwargs = VialKwargs(
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
                active=int(each_vial["active"]),
                base_thickness=float(each_vial["base_thickness"]),
            )

            vial = Vial(
                position=each_vial["position"],
                session_maker=SessionLocal,
                create_new=True,
                vial_name=each_vial["name"],
                **vkwargs,
            )

            vial_logger.info("Vial %s imported successfully", vial.position)
        except Exception as e:
            vial_logger.error(
                "Error occurred while importing vial %s: %s", each_vial["position"], e
            )
            vial_logger.error("Continuing....")
            vial_logger.exception(e)
