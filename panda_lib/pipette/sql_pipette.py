"""
This module contains functions to interact with the pipette_status table in the database.
"""
from configparser import ConfigParser
import json
from typing import Union
from panda_lib.sql_tools.panda_models import (
    Pipette,
    PipetteLog,
)  # Ensure you import your Base and Pipette model
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.config.config_tools import read_config
config = read_config()
precision = config.getint("OPTIONS", "precision")


def select_pipette_status(pipette_id: Union[int, None] = None):
    """
    Get the pipette status from the pipette_status table.
    And return a pipette instance to be applied to the pipette that
    is in memory.
    Returns:
        Pipette: The current pipette status.
    """
    with SessionLocal() as session:
        if pipette_id is None:
            pipette_status = (
                session.query(Pipette)
                .filter(Pipette.active == 1)
                .order_by(Pipette.updated.desc())
                .first()
            )
        else:
            pipette_status = (
                session.query(Pipette).filter(Pipette.id == pipette_id).first()
            )

        if pipette_status.contents:
            try:
                data = json.loads(pipette_status.contents)
            except json.JSONDecodeError:
                data = pipette_status.contents  # It was just a string

            pipette_status.contents = data

    return pipette_status


def update_pipette_status(
    capacity_ul: float,
    capacity_ml: float,
    volume_ul: float,
    volume_ml: float,
    contents: str,
    pipette_id: int,
):
    """
    Update the pipette status of the pipette with the matching id in the pipette_status table.
    If the pipette with the given id is not found, insert a new pipette.
    Args:
        capacity_ul (float): Capacity in microliters.
        capacity_ml (float): Capacity in milliliters.
        volume_ul (float): Volume in microliters.
        volume_ml (float): Volume in milliliters.
        contents (str): Contents of the pipette.
        pipette_id (int): ID of the pipette to update or insert.
    """
    with SessionLocal() as session:
        pipette_status = session.query(Pipette).filter(Pipette.id == pipette_id).first()
        if pipette_status is None:
            new_pipette_status = Pipette(
                capacity_ul=round(capacity_ul, precision),
                capacity_ml=round(capacity_ml, precision),
                volume_ul=round(volume_ul, precision),
                volume_ml=round(volume_ml, precision),
                contents=contents,
                id=pipette_id,
            )
            session.add(new_pipette_status)
        else:
            pipette_status.capacity_ul = round(capacity_ul, precision)
            pipette_status.capacity_ml = round(capacity_ml, precision)
            pipette_status.volume_ul = round(volume_ul, precision)
            pipette_status.volume_ml = round(volume_ml, precision)
            pipette_status.contents = contents
        session.commit()


def deincrement_use_count(pipette_id: int):
    """
    Decrement the use count of the pipette with the given id in the pipette_status table.
    Args:
        pipette_id (int): ID of the pipette to update.
    """
    with SessionLocal() as session:
        pipette_status = session.query(Pipette).filter(Pipette.id == pipette_id).first()
        try:
            previous_volume_ul = (
                session.query(PipetteLog)
                .filter(PipetteLog.pipette_id == pipette_id)
                .order_by(PipetteLog.updated.desc())
                .first()
                .volume_ul
            )
        except AttributeError:
            previous_volume_ul = None
        if (
            pipette_status is None
            or pipette_status.uses == 0
            or previous_volume_ul == pipette_status.volume_ul
        ):
            pass
        else:
            pipette_status.uses -= 1
            session.commit()


def select_current_pipette_id():
    """
    Get the active pipette status from the pipette_status table.
    And return a pipette instance to be applied to the pipette that
    is in memory.
    Returns:
        Pipette: The current pipette status.
    """
    with SessionLocal() as session:
        pipette_status = session.query(Pipette).filter(Pipette.active == 1).first()
        session.close()
    return pipette_status.id

def select_current_pipette_uses():
    """
    Get the active pipette status from the pipette_status table.
    And return a pipette record instance to be applied to the pipette that
    is in memory.
    Returns:
        Pipette: The current pipette status.
    """
    with SessionLocal() as session:
        pipette_status = session.query(Pipette).filter(Pipette.active == 1).first()
        session.close()
    return pipette_status.uses

def insert_new_pipette(
    pipette_id: Union[int, None] = None, capacity: float = 200, activate: bool = True
):
    """
    Insert a new pipette with the given id into the pipette_status table.
    If no pipette ID is given, a new ID is generated by incrementing from the highest ID.
    If no capacity is given, a capacity of 200 ul is assumed.
    Unless otherwise specified the pipette is activated.

    Args:
        pipette_id (int, optional): ID of the new pipette. Defaults to None.
        capacity (float, optional): Capacity of the new pipette. Defaults to 200.
        activate (bool, optional): Activate the new pipette. Defaults to True.

    """
    with SessionLocal() as session:
        if pipette_id is None:
            pipette_id = (
                session.query(Pipette).order_by(Pipette.id.desc()).first().id + 1
            )

        # Check if the id already exists
        if session.query(Pipette).filter(Pipette.id == pipette_id).first() is not None:
            print(f"Pipette with ID {pipette_id} already exists.")
            if activate:
                print(f"Activating pipette with ID {pipette_id}.")
                activate_pipette(pipette_id)
            return pipette_id

        # The pipette does not already exist
        else:
            new_pipette = Pipette(
                capacity_ul=round(capacity, precision),
                capacity_ml=round(capacity / 1000, precision),
                volume_ul=0,
                volume_ml=0,
                contents="{}",
                id=pipette_id,
                active=1 if activate else 0,
            )
            session.add(new_pipette)

        # Wrap up the transaction
        session.commit()
        activate_pipette(pipette_id)

    return pipette_id


def activate_pipette(pipette_id: int):
    """
    Activate the pipette with the given id in the pipette_status table by
    deactivating all other pipettes and activating the pipette with the given id.

    Args:
        pipette_id (int): ID of the pipette to activate.
    """
    with SessionLocal() as session:
        session.query(Pipette).update({Pipette.active: 0})
        session.query(Pipette).filter(Pipette.id == pipette_id).update(
            {Pipette.active: 1}
        )
        session.commit()
