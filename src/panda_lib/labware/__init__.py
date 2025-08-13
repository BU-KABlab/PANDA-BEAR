from typing import Tuple, Union

from panda_lib.types import Coordinates

from .errors import OverDraftException, OverFillException
from .schemas import (
    DeckObjectModel,
    PlateTypeModel,
    VesselModel,
    VialReadModel,
    VialWriteModel,
    WellplateReadModel,
    WellplateWriteModel,
    WellReadModel,
    WellWriteModel,
)
from .services import VialService, WellplateService, WellService
from .vials import StockVial, Vial, WasteVial, read_vials
from .wellplates import Well, Wellplate
from .tipracks import Tip, Rack

__all__ = [
    "Well",
    "Wellplate",
    "Vial",
    "StockVial",
    "WasteVial",
    "VialService",
    "WellService",
    "WellplateService",
    "DeckObjectModel",
    "VesselModel",
    "VialWriteModel",
    "VialReadModel",
    "WellWriteModel",
    "WellReadModel",
    "PlateTypeModel",
    "WellplateReadModel",
    "WellplateWriteModel",
    "OverFillException",
    "OverDraftException",
    "read_vials",
    "Tip",
    "Rack",
]


def get_xyz(
    labware: Union[Well, Wellplate, Vial, Coordinates],
) -> Tuple[float, float, float]:
    """
    Get the x, y, z coordinates of a well or wellplate.

    Args:
        well_or_wellplate (Union[Well, Wellplate, Vial]): The well, wellplate, or vial to get the coordinates of.

    Returns:
        tuple[float, float, float]: The x, y, z coordinates of the well, wellplate, or vial.
    """
    if isinstance(labware, (Well, Wellplate, Vial)):
        return labware.get_xyz()
    elif isinstance(labware, Coordinates):
        return labware.x, labware.y, labware.z
    else:
        raise TypeError("Invalid type for labware.")
