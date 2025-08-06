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
        rack: The rack to create tips for
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


def get_number_of_unused_tips(rack_id: Union[int, None] = None) -> int:
    """Query the tip_hx table and count tips with specific statuses.

    Counts tips with status in 'new', 'clear', 'queued' for the specified or
    current rack.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    int
        The number of tips with status in 'new', 'clear', 'queued'.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()
        result = (
            session.query(TipModel)
            .filter(TipModel.rack_id == rack_id)
            .filter(TipModel.status.in_(["new", "clear", "queued"]))
            .count()
        )
        return result


def select_current_rack_info() -> tuple[int, int, bool]:
    """Get the current rack information.

    Returns
    -------
    tuple[int, int, bool]
        A tuple containing:
        - rack ID (int)
        - rack type ID (int)
        - whether the rack is new (bool)
    """
    with SessionLocal() as session:
        statement = select(Racks).filter_by(current=1, panda_unit_id=get_unit_id())

        result: Racks = session.execute(statement).scalar()
        current_rack_id = result.id
        current_type_number = result.type_id
        is_new = check_if_current_rack_is_new()

    return current_rack_id, current_type_number, is_new


def select_rack_info(rack_id: int) -> Racks:
    """Get the rack information from the wellplates table.

    Parameters
    ----------
    rack_id : int
        The rack ID.

    Returns
    -------
    Racks
        The rack object that matches the rack_id.
    """
    with SessionLocal() as session:
        statement = select(Racks).filter_by(
            id=rack_id,
            panda_unit_id=read_config_value("PANDA", "unit_id", 99),
        )
        result = session.execute(statement).scalar_one_or_none()
        return result


def select_tip_ids(rack_id: Union[int, None] = None) -> List[str]:
    """Get the tip IDs from the tip_hx table.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    List[str]
        List of tip IDs.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(TipModel.tip_id)
            .filter(TipModel.rack_id == rack_id)
            .order_by(TipModel.tip_id.asc())
        )

        result = session.execute(statement).all()
        return [row[0] for row in result]


def select_rack_tips(rack_id: Union[int, None] = None) -> Sequence:
    """Select all tips from the tip_hx table for a specific rack.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    Sequence
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(
                TipModel.rack_id,
                Racks.type_id,
                TipModel.tip_id,
                TipModel.status,
                TipModel.status_date,
                TipModel.contents,
                TipModel.experiment_id,
                TipModel.project_id,
                TipModel.volume,
                TipModel.coordinates,
            )
            .join(Racks, TipModel.rack_id == Racks.id)
            .join(RackTypes, Racks.type_id == RackTypes.id)
            .filter(TipModel.rack_id == rack_id)
            .order_by(TipModel.tip_id.asc())
        )

        result = session.execute(statement).all()
        if result == []:
            return None

        return result


def select_tip_status(tip_id: str, rack_id: Union[int, None] = None) -> str:
    """Get the status of a tip from the tip_hx table.

    Parameters
    ----------
    tip_id : str
        The tip ID.
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    str
        The status of the tip.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(TipModel.status)
            .filter(TipModel.rack_id == rack_id)
            .filter(TipModel.tip_id == tip_id)
        )

        result = session.execute(statement).scalar_one_or_none()
        return result


def count_tips_with_new_status(rack_id: Union[int, None] = None) -> int:
    """Count the number of tips with a status of 'new' in the tip_hx table.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    int
        The number of tips with a status of 'new'.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(func.count())
            .select_from(TipModel)
            .filter(TipModel.status == "new")
            .filter(TipModel.rack_id == rack_id)
        )

        result = session.execute(statement).scalar_one()
        return result


def select_next_available_tip(rack_id: Union[int, None] = None) -> str:
    """Choose the next available tip in the tip_hx table.

    Parameters
    ----------
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    str
        The tip ID of the next available tip.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(TipModel.tip_id)
            .filter(TipModel.status == "new")
            .filter(TipModel.rack_id == rack_id)
            .order_by(
                func.substr(TipModel.tip_id, 1, 1),
                cast(func.substr(TipModel.tip_id, 2), Integer).asc(),
            )
        )

        result = session.execute(statement).first()
        if result is None:
            return None
        return result[0]


def save_tip_to_db(tip_to_save: object) -> None:
    """First check if the tip is in the table. If so update the tip where the
    values are different. Otherwise insert the tip into the table.

    Parameters
    ----------
    tip_to_save : object
        The tip object to save.
    """
    with SessionLocal() as session:
        if tip_to_save.rack_id in [None, 0]:
            current_rack_statement = select(Racks.id).filter(
                Racks.current == 1
            )
            tip_to_save.rack_id = session.execute(
                current_rack_statement
            ).scalar_one()

        # Instead we will update the status of the tip if it already exists
        update_statement = (
            update(TipModel)
            .where(TipModel.rack_id == tip_to_save.rack_id)
            .where(TipModel.tip_id == tip_to_save.tip_id)
            .values(
                experiment_id=tip_to_save.experiment_id,
                project_id=tip_to_save.project_id,
                status=tip_to_save.status,
                status_date=datetime.now(tz=timezone.utc).isoformat(),
                coordinates=json.dumps(asdict(tip_to_save.coordinates)),
            )
        )
        session.execute(update_statement)
        session.commit()


def save_tips_to_db(tips_to_save: List[object]) -> None:
    """First check if the tip is in the table. If so update the tip where the
    values are different. Otherwise insert the tip into the table.

    Parameters
    ----------
    wells_to_save : List[object]
        List of tip objects to save.
    """
    with SessionLocal() as session:
        for tip in tips_to_save:
            if tip.rack_id in [None, 0]:
                current_plate_statement = select(Racks.id).filter(
                    Racks.current == 1
                )
                tip.rack_id = session.execute(current_plate_statement).scalar_one()

            # Check if tip exists
            exists_statement = select(TipModel).filter(
                TipModel.rack_id == tip.rack_id, TipModel.tip_id == tip.tip_id
            )
            exists = session.execute(exists_statement).scalar_one_or_none()

            if exists:
                # Update existing tip
                update_statement = (
                    update(TipModel)
                    .where(TipModel.rack_id == tip.rack_id)
                    .where(TipModel.tip_id == tip.tip_id)
                    .values(
                        experiment_id=tip.experiment_id,
                        project_id=tip.project_id,
                        status=tip.status,
                        status_date=datetime.now(tz=timezone.utc).isoformat(),
                        coordinates=json.dumps(asdict(tip.coordinates)),
                    )
                )
                session.execute(update_statement)
            else:
                # Insert new tip
                insert_statement = insert(TipModel).values(
                    rack_id=tip.rack_id,
                    tip_id=tip.tip_id,
                    experiment_id=tip.experiment_id,
                    project_id=tip.project_id,
                    status=tip.status,
                    status_date=datetime.now(tz=timezone.utc).isoformat(),
                    coordinates=json.dumps(asdict(tip.coordinates)),
                )
                session.execute(insert_statement)

        session.commit()


def insert_tip(tip_to_insert: object) -> None:
    """Insert a tip into the tip_hx table.

    Insert_well will accept a tip object, and using its attributes, insert a new
    row into the tip_hx table.

    Parameters
    ----------
    tip_to_insert : object
        The tip to insert.
    """
    with SessionLocal() as session:
        session.add(TipModel(**tip_to_insert.__dict__))
        session.commit()


def update_tip(tip_to_update: object) -> None:
    """Updating the entry in the tip_hx table that matches the tip and rack ids.

    Parameters
    ----------
    tip_to_update : object
        The tip to update.
    """
    with SessionLocal() as session:
        update_statement = (
            update(TipModel)
            .where(TipModel.rack_id == tip_to_update.tip_data.rack_id)
            .where(TipModel.tip_id == tip_to_update.tip_data.tip_id)
            .values(
                experiment_id=tip_to_update.tip_data.experiment_id,
                project_id=tip_to_update.tip_data.project_id,
                status=tip_to_update.tip_data.status,
                status_date=datetime.now().isoformat(timespec="seconds"),
                coordinates=json.dumps(tip_to_update.tip_data.coordinates),
            )
        )
        session.execute(update_statement)
        session.commit()


def get_tip_by_id(
    tip_id: str,
    rack_id: Union[int, None] = None,
) -> TipModel:
    """Get a tip from the tip_hx table.

    Parameters
    ----------
    tip_id : str
        The tip ID.
    rack_id : int, optional
        The rack ID. If None, uses current rack.

    Returns
    -------
    TipModel
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        statement = (
            select(TipModel)
            .filter(TipModel.rack_id == rack_id)
            .filter(TipModel.tip_id == tip_id)
        )

        result = session.execute(statement).scalar_one_or_none()
        if result is None:
            return None

        return result


def get_tip_by_experiment_id(experiment_id: str) -> Tuple:
    """Get a tip from the tip_hx table by experiment ID.

    Parameters
    ----------
    experiment_id : str
        The experiment ID.

    Returns
    -------
    Tuple
        The tip.
    """
    with SessionLocal() as session:
        statement = select(TipModel).filter(TipModel.experiment_id == experiment_id)
        result = session.execute(statement).scalar_one_or_none()
        return result


def select_tip_characteristics(type_id: int) -> RackTypes:
    """Select the tip characteristics from the well_types table.

    Parameters
    ----------
    type_id : int
        The tip type ID.

    Returns
    -------
    RackTypes
        The SQL Alchemy object for the tip type.
    """
    with SessionLocal() as session:
        statement = select(RackTypes).filter(RackTypes.id == type_id)
        result = session.execute(statement).scalar_one_or_none()
        if result is None:
            logger.warning(f"No rack type found with ID {type_id}")
            return None
        return result


def update_tip_coordinates(
    tip_id: str, rack_id: Union[int, None], coordinates: object
) -> None:
    """Update the coordinates of an individal tip in the tip_hx table.

    Parameters
    ----------
    tip_id : str
        The tip ID.
    rack_id : int
        The rack ID.
    coordinates : object
        The coordinates.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        update_stmt = (
            update(TipModel)
            .where(TipModel.rack_id == rack_id)
            .where(TipModel.tip_id == tip_id)
        )
        update_stmt = update_stmt.values(
            coordinates=json.dumps(asdict(coordinates)),
        )
        session.execute(update_stmt)
        session.commit()


def update_tip_status(
    tip_id: str, rack_id: Union[None, int] = None, status: Union[None, str] = None
) -> None:
    """Update the status of a tip in the tip_hx table.

    Parameters
    ----------
    tip_id : str
        The tip ID.
    rack_id : int, optional
        The rack ID. If None, uses current rack.
    status : str, optional
        The status. If None, uses current status.
    """
    with SessionLocal() as session:
        if rack_id is None:
            rack_id = select_current_rack_id()

        if status is None:
            status = select_tip_status(tip_id, rack_id)

        update_statement = (
            update(TipModel)
            .where(TipModel.rack_id == rack_id)
            .where(TipModel.tip_id == tip_id)
            .values(
                status=status, status_date=datetime.now().isoformat(timespec="seconds")
            )
        )

        session.execute(update_statement)
        session.commit()


# endregion
