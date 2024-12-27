"""Utilities for working with protocols in the database."""

import os
from ast import List

from panda_lib.config.config_tools import read_config

# region Protocols
from panda_lib.errors import ProtocolNotFoundError

# import sqlite3
# from panda_lib.config.config import SQL_DB_PATH
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import Protocols


class ProtocolEntry:
    """A class to represent a protocol entry in the database."""

    def __init__(self, protocol_id, project, name, filepath):
        self.protocol_id = protocol_id
        self.project = project
        self.name = name
        self.filepath = filepath

    def __str__(self):
        return f"{self.protocol_id}: {self.name}"


def select_protocols() -> List[ProtocolEntry]:
    """
    Get all protocols from the database.

    Args:
        None

    Returns:
        list: A list of all protocols in the database.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get all protocols from the database
    # cursor.execute("SELECT * FROM protocols")
    # protocols = cursor.fetchall()

    # conn.close()

    # protocol_entries = []
    # for protocol in protocols:
    #     protocol_entry = ProtocolEntry(*protocol)
    #     protocol_entries.append(protocol_entry)

    # return protocol_entries

    with SessionLocal() as session:
        protocols = session.query(Protocols).all()

    protocol_entries = []
    for protocol in protocols:
        protocol_entry = ProtocolEntry(
            protocol.id, protocol.project, protocol.name, protocol.filepath
        )
        protocol_entries.append(protocol_entry)

    return protocol_entries


def select_protocol(protocol_id) -> ProtocolEntry:
    """
    Get a protocol from the database.

    Args:
        protocol_id (int): The ID of the protocol to get.

    Returns:
        ProtocolEntry: The protocol from the database.
    """

    with SessionLocal() as session:
        if isinstance(protocol_id, str):
            result = (
                session.query(Protocols).filter(Protocols.name == protocol_id).first()
            )
            if result is None:  # Check if the protocol_id is a file name
                result = (
                    session.query(Protocols)
                    .filter(Protocols.name == protocol_id + ".py")
                    .first()
                )
        else:
            result = (
                session.query(Protocols).filter(Protocols.id == protocol_id).first()
            )
        if result is None:
            raise ProtocolNotFoundError(f"Protocol with id {protocol_id} not found.")
        protocol_entry = ProtocolEntry(
            result.id, result.project, result.name, result.filepath
        )

    return protocol_entry


def insert_protocol(protocol_id, project, name, filepath):
    """
    Insert a protocol into the database.

    Args:
        protocol_id (int): The ID of the protocol.
        project (str): The project of the protocol.
        name (str): The name of the protocol.
        filepath (str): The filepath of the protocol.

    Returns:
        None
    """

    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Clean the name of any file extensions
    # name = name.split(".")[0]

    # # Insert the protocol into the database
    # cursor.execute(
    #     "INSERT INTO protocols (id, project, name, filepath) VALUES (?, ?, ?, ?)",
    #     (protocol_id, project, name, filepath),
    # )

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        # Clean the name of any file extensions, split on "." and take the first element
        name = name.split(".")[0]

        # Insert the protocol into the database
        session.add(
            Protocols(id=protocol_id, project=project, name=name, filepath=filepath)
        )

        session.commit()


def update_protocol(protocol_id, new_name):
    """
    Update the name of a protocol in the database.

    Args:
        protocol_id (int): The ID of the protocol to update.
        new_name (str): The new name to set for the protocol.

    Returns:
        None
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Update the name of the protocol in the database
    # cursor.execute(
    #     "UPDATE protocols SET name = ? WHERE id = ?", (new_name, protocol_id)
    # )

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        # Update the name of the protocol in the database
        session.query(Protocols).filter(Protocols.id == protocol_id).update(
            {"name": new_name}
        )


def delete_protocol(protocol_id):
    """
    Delete a protocol from the database.

    Args:
        protocol_id (int): The ID of the protocol.

    Returns:
        None
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Delete the protocol from the database
    # cursor.execute("DELETE FROM protocols WHERE id = ?", (protocol_id,))

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        # Delete the protocol from the database
        session.query(Protocols).filter(Protocols.id == protocol_id).delete()


def read_in_protocols():
    """
    Read in all protocol files from the current protocols folder, assigning an id to each one.
    Ignoring this file as well as any files that are already in the database.
    Args:
        None

    Returns:
        None
    """

    # Get the protocols folder from the environment variables
    # try:
    #     protocols = os.environ["PANDA_SDL_PROTOCOLS_DIR"]
    # except KeyError as e:
    #     raise ValueError(
    #         "PANDA_SDL_PROTOCOLS_DIR environment variable not set in .env file."
    #     ) from e
    config = read_config()
    protocols = config.get("GENERAL", "protocols_dir")

    # Get all files in the protocols folder
    protocols = os.listdir(protocols)

    # Remove an non .py files
    protocols = [protocol for protocol in protocols if protocol.endswith(".py")]
    # Get the current protocols from the database
    current_protocols = select_protocols()

    # Get the current protocol ids
    current_protocol_ids = [protocol.protocol_id for protocol in current_protocols]

    # Get the next protocol id
    if current_protocol_ids:
        next_protocol_id = max(current_protocol_ids) + 1
    else:
        next_protocol_id = 1

    # Get the filenames of the current protocols
    # current_protocol_filenames = [protocol.name for protocol in current_protocols]
    # get filepaths of current protocols
    current_protocol_filepaths = [protocol.filepath for protocol in current_protocols]
    # Iterate through the protocols
    for protocol in protocols:
        # If the protocol is not already in the database
        if protocol not in current_protocol_filepaths:
            # Insert the protocol into the database
            insert_protocol(next_protocol_id, "", protocol[:-3], protocol)
            next_protocol_id += 1
        else:
            # Get the id of the protocol
            protocol_id = current_protocols[
                current_protocol_filepaths.index(protocol)
            ].protocol_id

            # Update the protocol in the database
            update_protocol(protocol_id, protocol)

    # Delete any protocols that are no longer in the protocols folder
    for protocol in current_protocols:
        if protocol.filepath not in protocols:
            delete_protocol(protocol.protocol_id)


def select_protocol_id(protocol_name) -> int:
    """
    Get the id of a protocol from the database.

    Args:
        protocol_name (str): The name of the protocol.

    Returns:
        int: The id of the protocol.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get the id of the protocol from the database
    # cursor.execute("SELECT id FROM protocols WHERE name = ?", (protocol_name,))
    # protocol_id = cursor.fetchone()[0]

    # conn.close()

    # return protocol_id

    with SessionLocal() as session:
        result = (
            session.query(Protocols).filter(Protocols.name == protocol_name).first()
        )
        if result is None:
            raise ProtocolNotFoundError(
                f"Protocol with name {protocol_name} not found."
            )
        protocol_id = result.id

    return protocol_id


def select_protocol_name(protocol_id) -> str:
    """
    Get the name of a protocol from the database.

    Args:
        protocol_id (int): The id of the protocol.

    Returns:
        str: The name of the protocol.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get the name of the protocol from the database
    # cursor.execute("SELECT name FROM protocols WHERE id = ?", (protocol_id,))
    # protocol_name = cursor.fetchone()[0]

    # conn.close()

    # return protocol_name

    with SessionLocal() as session:
        result = session.query(Protocols).filter(Protocols.id == protocol_id).first()
        if result is None:
            raise ProtocolNotFoundError(f"Protocol with id {protocol_id} not found.")
        protocol_name = result.name

    return protocol_name


# end region
if __name__ == "__main__":
    read_in_protocols()
    protocols_in_db = select_protocols()
    for each_protocol in protocols_in_db:
        print(each_protocol)
