from typing import Dict, Optional, TypedDict

from sqlalchemy.orm import Session

from .errors import OverDraftException, OverFillException  # Custom exceptions
from .schemas import VialReadModel, VialWriteModel  # Pydantic models
from .services import VialService
from .utilities import Coordinates


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


class Vial:
    def __init__(
        self,
        position: str,
        session: Session,
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
        self.session = session
        self.service = VialService(self.session)
        self.vial_data: Optional[VialReadModel] = None

        if create_new:
            self.create_new_vial(**kwargs)
        else:
            self.load_vial()

    @property
    def volume(self) -> float:
        """Returns the current volume of the vial."""
        return self.vial_data.volume

    @property
    def contents(self) -> Dict[str, float]:
        """Returns the contents of the vial."""
        return self.vial_data.contents

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
    def withdrawal_height(self) -> float:
        """Returns the height of the vial from which contents are withdrawn."""
        height = self.vial_data.volume_height - 1
        if height < self.vial_data.dead_volume:
            return self.vial_data.dead_volume / (3.14 * self.vial_data.radius**2)

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
        self.vial_data.volume = self.vial_data.capacity
        self.vial_data.contents = (
            {}
            if self.vial_data.category == 1
            else {next(iter(self.vial_data.contents)): self.vial_data.capacity}
        )
        self.vial_data.contamination = 0
        self.save()

    def __repr__(self):
        return f"<Vial(position={self.position}, volume={self.vial_data.volume}, contents={self.vial_data.contents})>"
