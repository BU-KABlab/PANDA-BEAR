"""
SQL Tools Tip Rack Queries

This module contains functions for querying and manipulating tip racks and tips.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sqlalchemy import Integer, cast, func, insert, select, update
from sqlalchemy.orm import Session

from panda_shared.config.config_tools import read_config_value
from panda_shared.db_setup import SessionLocal

from ..models.racks import RackTypes, TipModel, Racks
from .queue import get_unit_id

logger = logging.getLogger("sql_tools")


def get_rack_by_id(rack_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a tip rack by its ID.

    Args:
        rack_id: The ID of the tip rack to retrieve

    Returns:
        A dictionary with tip rack data if found, None otherwise
    """
    with SessionLocal() as session:
        stmt = select(Racks).where(Racks.id == rack_id)
        rack = session.scalars(stmt).first()

        if not rack:
            return None

        return {
            "id": rack.id,
            "rack_type_id": rack.rack_type_id,
            "rack_type_name": rack.rack_type.name if rack.rack_type else None,
            "barcode": rack.barcode,
            "label": rack.label,
            "created_at": rack.created_at.isoformat() if rack.created_at else None,
        }


def get_all_racks() -> List[Dict[str, Any]]:
    """
    Get all tip racks in the database.

    Returns:
        A list of dictionaries with tip rack data
    """
    with SessionLocal() as session:
        stmt = select(Racks).order_by(Racks.id)
        racks = session.scalars(stmt).all()

        result = []
        for rack in racks:
            result.append(
                {
                    "id": rack.id,
                    "rack_type_id": rack.rack_type_id,
                    "rack_type_name": rack.rack_type.name
                    if rack.rack_type
                    else None,
                    "barcode": rack.barcode,
                    "label": rack.label,
                    "created_at": rack.created_at.isoformat()
                    if rack.created_at
                    else None,
                }
            )

        return result


def add_rack(
    rack_type_id: int, barcode: Optional[str] = None, label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new tip rack to the database.

    Args:
        rack_type_id: ID of the rack type
        barcode: Optional barcode for the rack
        label: Optional human-readable label

    Returns:
        A dictionary with the created tip rack data
    """
    with SessionLocal() as session:
        # Check if rack type exists
        rack_type = session.get(RackTypes, rack_type_id)
        if not rack_type:
            raise ValueError(f"Rack type with id {rack_type_id} not found")

        # Create new tip rack
        rack = Racks(rack_type_id=rack_type_id, barcode=barcode, label=label)

        session.add(rack)
        session.commit()
        session.refresh(rack)

        # Create tips for this rack
        _create_tips_for_rack(session, rack)

        return {
            "id": rack.id,
            "rack_type_id": rack.rack_type_id,
            "rack_type_name": rack.rack_type.name,
            "barcode": rack.barcode,
            "label": rack.label,
            "created_at": rack.created_at.isoformat() if rack.created_at else None,
        }


def get_tip_history(tip_id: int) -> List[Dict[str, Any]]:
    """
    Get the history of experiments for a specific tip.

    Args:
        tip_id: The ID of the tip to check history for

    Returns:
        A list of dictionaries with experiment history
    """
    # This would typically join tips with experiment history table
    # Implementation depends on the specific schema
    return []


def _create_tips_for_rack(session: Session, rack: Racks) -> None:
    """
    Create the tip records for a new tip rack.

    Args:
        session: SQLAlchemy session
        rack: The wellplate to create wells for
    """
    rack_type = rack.rack_type

    tips = []
    for row in range(rack_type.rows):
        for col in range(rack_type.columns):
            tip = TipModel(rack_id=rack.id, row=row, column=col)
            tips.append(tip)

    session.add_all(tips)
    session.commit()


def check_if_rack_type_exists(type_id: int) -> bool:
    """Check if a rack type exists in the rack_types table.

    Parameters
    ----------
    type_id : int
        The ID of the rack type to check.

    Returns
    -------
    bool
        True if the rack type exists, False otherwise.
    """
    with SessionLocal() as session:
        return (
            session.execute(
                select(RackTypes).filter(RackTypes.id == type_id)
            ).scalar()
            is not None
        )


def select_current_rack_id() -> int:
    """Get the current rack ID.

    Returns
    -------
    int
        The current rack ID.
    """
    with SessionLocal() as session:
        statement = select(Racks).filter_by(
            current=1, panda_unit_id=read_config_value("PANDA", "unit_id", 99)
        )
        result: Racks = session.execute(statement).scalar_one_or_none()
        if result is None:
            return None
        return result.id


def check_if_current_rack_is_new() -> bool:
    """Check if the current rack is new.

    Returns
    -------
    bool
        True if all tips in current tip rack have 'new' status, False otherwise.
    """
    with SessionLocal() as session:
        current_rack_id = select_current_rack_id()

        if current_rack_id is None:
            logger.info("No current tip rack found")
            return False

        result = session.execute(
            select(TipModel.status).filter(TipModel.rack_id == current_rack_id)
        ).all()

        if not result:
            return False

        for row in result:
            if row[0] != "new":
                return False
        return True


def get_number_of_tips(rack_id: Union[int, None] = None) -> int:
    """Get the number of tips in the tip_hx table for the given or current tip rack.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    int
        The number of tips.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()
        result = session.query(TipModel).filter(TipModel.rack_id == rack_id).count()
        return result

# TODO: ENDED HERE.......Continue fixing below this line
def get_number_of_unused_tips(plate_id: Union[int, None] = None) -> int:
    """Query the tip_hx table and count tips with specific statuses.

    Counts tips with status in 'new', 'clear', 'queued' for the specified or
    current wellplate.

    Parameters
    ----------
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    int
        The number of wells with status in 'new', 'clear', 'queued'.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()
        result = (
            session.query(WellModel)
            .filter(WellModel.plate_id == plate_id)
            .filter(WellModel.status.in_(["new", "clear", "queued"]))
            .count()
        )
        return result


def select_current_wellplate_info() -> tuple[int, int, bool]:
    """Get the current wellplate information.

    Returns
    -------
    tuple[int, int, bool]
        A tuple containing:
        - wellplate ID (int)
        - wellplate type ID (int)
        - whether the wellplate is new (bool)
    """
    with SessionLocal() as session:
        statement = select(Wellplates).filter_by(current=1, panda_unit_id=get_unit_id())

        result: Wellplates = session.execute(statement).scalar()
        current_plate_id = result.id
        current_type_number = result.type_id
        is_new = check_if_current_wellplate_is_new()

    return current_plate_id, current_type_number, is_new


def select_wellplate_info(plate_id: int) -> Wellplates:
    """Get the wellplate information from the wellplates table.

    Parameters
    ----------
    plate_id : int
        The rack ID.

    Returns
    -------
    Wellplates
        The wellplate object that matches the plate_id.
    """
    with SessionLocal() as session:
        statement = select(Wellplates).filter_by(
            id=plate_id,
            panda_unit_id=read_config_value("PANDA", "unit_id", 99),
        )
        result = session.execute(statement).scalar_one_or_none()
        return result


def select_well_ids(plate_id: Union[int, None] = None) -> List[str]:
    """Get the well IDs from the well_hx table.

    Parameters
    ----------
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    List[str]
        List of well IDs.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(WellModel.well_id)
            .filter(WellModel.plate_id == plate_id)
            .order_by(WellModel.well_id.asc())
        )

        result = session.execute(statement).all()
        return [row[0] for row in result]


def select_wellplate_wells(plate_id: Union[int, None] = None) -> Sequence:
    """Select all wells from the well_hx table for a specific wellplate.

    Parameters
    ----------
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    Sequence
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(
                WellModel.plate_id,
                Wellplates.type_id,
                WellModel.well_id,
                WellModel.status,
                WellModel.status_date,
                WellModel.contents,
                WellModel.experiment_id,
                WellModel.project_id,
                WellModel.volume,
                WellModel.coordinates,
                PlateTypes.capacity_ul,
                PlateTypes.gasket_height_mm,
            )
            .join(Wellplates, WellModel.plate_id == Wellplates.id)
            .join(PlateTypes, Wellplates.type_id == PlateTypes.id)
            .filter(WellModel.plate_id == plate_id)
            .order_by(WellModel.well_id.asc())
        )

        result = session.execute(statement).all()
        if result == []:
            return None

        return result


def select_well_status(well_id: str, plate_id: Union[int, None] = None) -> str:
    """Get the status of a well from the well_hx table.

    Parameters
    ----------
    well_id : str
        The well ID.
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    str
        The status of the well.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(WellModel.status)
            .filter(WellModel.plate_id == plate_id)
            .filter(WellModel.well_id == well_id)
        )

        result = session.execute(statement).scalar_one_or_none()
        return result


def count_wells_with_new_status(plate_id: Union[int, None] = None) -> int:
    """Count the number of wells with a status of 'new' in the well_hx table.

    Parameters
    ----------
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    int
        The number of wells with a status of 'new'.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(func.count())
            .select_from(WellModel)
            .filter(WellModel.status == "new")
            .filter(WellModel.plate_id == plate_id)
        )

        result = session.execute(statement).scalar_one()
        return result


def select_next_available_well(plate_id: Union[int, None] = None) -> str:
    """Choose the next available well in the well_hx table.

    Parameters
    ----------
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    str
        The well ID of the next available well.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(WellModel.well_id)
            .filter(WellModel.status == "new")
            .filter(WellModel.plate_id == plate_id)
            .order_by(
                func.substr(WellModel.well_id, 1, 1),
                cast(func.substr(WellModel.well_id, 2), Integer).asc(),
            )
        )

        result = session.execute(statement).first()
        if result is None:
            return None
        return result[0]


def save_well_to_db(well_to_save: object) -> None:
    """First check if the well is in the table. If so update the well where the
    values are different. Otherwise insert the well into the table.

    Parameters
    ----------
    well_to_save : object
        The well object to save.
    """
    with SessionLocal() as session:
        if well_to_save.plate_id in [None, 0]:
            current_plate_statement = select(Wellplates.id).filter(
                Wellplates.current == 1
            )
            well_to_save.plate_id = session.execute(
                current_plate_statement
            ).scalar_one()

        # Instead we will update the status of the well if it already exists
        update_statement = (
            update(WellModel)
            .where(WellModel.plate_id == well_to_save.plate_id)
            .where(WellModel.well_id == well_to_save.well_id)
            .values(
                experiment_id=well_to_save.experiment_id,
                project_id=well_to_save.project_id,
                status=well_to_save.status,
                status_date=datetime.now(tz=timezone.utc).isoformat(),
                contents=json.dumps(well_to_save.contents),
                volume=well_to_save.volume,
                coordinates=json.dumps(asdict(well_to_save.coordinates)),
            )
        )
        session.execute(update_statement)
        session.commit()


def save_wells_to_db(wells_to_save: List[object]) -> None:
    """First check if the well is in the table. If so update the well where the
    values are different. Otherwise insert the well into the table.

    Parameters
    ----------
    wells_to_save : List[object]
        List of well objects to save.
    """
    with SessionLocal() as session:
        for well in wells_to_save:
            if well.plate_id in [None, 0]:
                current_plate_statement = select(Wellplates.id).filter(
                    Wellplates.current == 1
                )
                well.plate_id = session.execute(current_plate_statement).scalar_one()

            # Check if well exists
            exists_statement = select(WellModel).filter(
                WellModel.plate_id == well.plate_id, WellModel.well_id == well.well_id
            )
            exists = session.execute(exists_statement).scalar_one_or_none()

            if exists:
                # Update existing well
                update_statement = (
                    update(WellModel)
                    .where(WellModel.plate_id == well.plate_id)
                    .where(WellModel.well_id == well.well_id)
                    .values(
                        experiment_id=well.experiment_id,
                        project_id=well.project_id,
                        status=well.status,
                        status_date=datetime.now(tz=timezone.utc).isoformat(),
                        contents=json.dumps(well.contents),
                        volume=well.volume,
                        coordinates=json.dumps(asdict(well.coordinates)),
                    )
                )
                session.execute(update_statement)
            else:
                # Insert new well
                insert_statement = insert(WellModel).values(
                    plate_id=well.plate_id,
                    well_id=well.well_id,
                    experiment_id=well.experiment_id,
                    project_id=well.project_id,
                    status=well.status,
                    status_date=datetime.now(tz=timezone.utc).isoformat(),
                    contents=json.dumps(well.contents),
                    volume=well.volume,
                    coordinates=json.dumps(asdict(well.coordinates)),
                )
                session.execute(insert_statement)

        session.commit()


def insert_well(well_to_insert: object) -> None:
    """Insert a well into the well_hx table.

    Insert_well will accept a well object, and using its attributes, insert a new
    row into the well_hx table.

    Parameters
    ----------
    well_to_insert : object
        The well to insert.
    """
    with SessionLocal() as session:
        session.add(WellModel(**well_to_insert.__dict__))
        session.commit()


def update_well(well_to_update: object) -> None:
    """Updating the entry in the well_hx table that matches the well and rack ids.

    Parameters
    ----------
    well_to_update : object
        The well to update.
    """
    with SessionLocal() as session:
        update_statement = (
            update(WellModel)
            .where(WellModel.plate_id == well_to_update.well_data.plate_id)
            .where(WellModel.well_id == well_to_update.well_data.well_id)
            .values(
                experiment_id=well_to_update.well_data.experiment_id,
                project_id=well_to_update.well_data.project_id,
                status=well_to_update.well_data.status,
                status_date=datetime.now().isoformat(timespec="seconds"),
                contents=json.dumps(well_to_update.well_data.contents),
                volume=well_to_update.volume,
                coordinates=json.dumps(well_to_update.well_data.coordinates),
            )
        )
        session.execute(update_statement)
        session.commit()


def get_well_by_id(
    well_id: str,
    plate_id: Union[int, None] = None,
) -> WellModel:
    """Get a well from the well_hx table.

    Parameters
    ----------
    well_id : str
        The well ID.
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.

    Returns
    -------
    WellModel
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        statement = (
            select(WellModel)
            .filter(WellModel.plate_id == plate_id)
            .filter(WellModel.well_id == well_id)
        )

        result = session.execute(statement).scalar_one_or_none()
        if result is None:
            return None

        return result


def get_well_by_experiment_id(experiment_id: str) -> Tuple:
    """Get a well from the well_hx table by experiment ID.

    Parameters
    ----------
    experiment_id : str
        The experiment ID.

    Returns
    -------
    Tuple
        The well.
    """
    with SessionLocal() as session:
        statement = select(WellModel).filter(WellModel.experiment_id == experiment_id)
        result = session.execute(statement).scalar_one_or_none()
        return result


def select_well_characteristics(type_id: int) -> PlateTypes:
    """Select the well characteristics from the well_types table.

    Parameters
    ----------
    type_id : int
        The well type ID.

    Returns
    -------
    PlateTypes
        The SQL Alchemy object for the well type.
    """
    with SessionLocal() as session:
        statement = select(PlateTypes).filter(PlateTypes.id == type_id)
        result = session.execute(statement).scalar_one_or_none()
        if result is None:
            logger.warning(f"No rack type found with ID {type_id}")
            return None
        return result


def update_well_coordinates(
    well_id: str, plate_id: Union[int, None], coordinates: object
) -> None:
    """Update the coordinates of an individal well in the well_hx table.

    Parameters
    ----------
    well_id : str
        The well ID.
    plate_id : int
        The rack ID.
    coordinates : object
        The coordinates.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        update_stmt = (
            update(WellModel)
            .where(WellModel.plate_id == plate_id)
            .where(WellModel.well_id == well_id)
        )
        update_stmt = update_stmt.values(
            coordinates=json.dumps(asdict(coordinates)),
        )
        session.execute(update_stmt)
        session.commit()


def update_well_status(
    well_id: str, plate_id: Union[None, int] = None, status: Union[None, str] = None
) -> None:
    """Update the status of a well in the well_hx table.

    Parameters
    ----------
    well_id : str
        The well ID.
    plate_id : int, optional
        The rack ID. If None, uses current wellplate.
    status : str, optional
        The status. If None, uses current status.
    """
    with SessionLocal() as session:
        if plate_id is None:
            plate_id = select_current_wellplate_id()

        if status is None:
            status = select_well_status(well_id, plate_id)

        update_statement = (
            update(WellModel)
            .where(WellModel.plate_id == plate_id)
            .where(WellModel.well_id == well_id)
            .values(
                status=status, status_date=datetime.now().isoformat(timespec="seconds")
            )
        )

        session.execute(update_statement)
        session.commit()


# endregion
