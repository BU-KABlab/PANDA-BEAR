"""
This module contains functions for interacting with the generators table in
the database.

The functions in this module allow you to get, insert, update, and delete
generators in the database. The module also contains functions for reading in
generators from the generators folder and running generators.
"""

import importlib
import os

# import sqlite3

from panda_lib.config.config_tools import read_config
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import ExperimentGenerators

# from sqlalchemy.orm import Session

# region Generators
config = read_config()
# if config.getboolean("OPTIONS", "TESTING"):
#     sql_db_path = config.get("TESTING", "testing_db_address")
# else:
#     sql_db_path = config.get("PRODUCTION", "production_db_address")

# SQL_DB_PATH = sql_db_path


class GeneratorEntry:
    """A class to represent a generator entry in the database."""

    def __init__(self, generator_id, project_id, protocol_id, name, filepath):
        self.generator_id = generator_id
        self.project_id = project_id
        self.protocol_id = protocol_id
        self.name = name
        self.filepath = filepath

    def __str__(self):
        return f"{self.generator_id}: {self.name}"


def get_generators() -> list:
    """
    Get all generators from the database.

    Args:
        None

    Returns:
        list: A list of all generators in the database.
    """

    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get all generators from the database
    # cursor.execute("SELECT * FROM generators")
    # generators = cursor.fetchall()

    # conn.close()

    # generator_entries = []
    # for generator in generators:
    #     generator_entry = GeneratorEntry(*generator)
    #     generator_entries.append(generator_entry)

    # return generator_entries

    with SessionLocal() as session:
        return session.query(ExperimentGenerators).all()


def get_generator_by_id(generator_id) -> GeneratorEntry:
    """
    Get a generator from the database.

    Args:
        generator_id (int): The ID of the generator to get.

    Returns:
        GeneratorEntry: The generator from the database.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get the generator from the database
    # cursor.execute("SELECT * FROM generators WHERE id = ?", (generator_id,))
    # generator = cursor.fetchone()

    # conn.close()

    # generator_entry = GeneratorEntry(*generator)
    # return generator_entry

    with SessionLocal() as session:
        return (
            session.query(ExperimentGenerators)
            .filter(ExperimentGenerators.id == generator_id)
            .first()
        )


def insert_generator(generator_id, project_id, protocol_id, name, filepath):
    """
    Insert a generator into the database.

    Args:
        generator_id (int): The ID of the generator.
        project_id (int): The project ID of the generator.
        protocol_id (int): The protocol ID of the generator.
        name (str): The name of the generator.
        filepath (str): The filepath of the generator.

    Returns:
        None
    """

    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Insert the generator into the database
    # cursor.execute(
    #     """
    #     INSERT INTO generators (
    #         id,
    #         project_id,
    #         protocol_id,
    #         name,
    #         filepath
    #         )
    #     VALUES (?, ?, ?, ?, ?)
    #     """,
    #     (generator_id, project_id, protocol_id, name, filepath),
    # )

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        session.add(
            ExperimentGenerators(
                id=generator_id,
                project_id=project_id,
                protocol_id=protocol_id,
                name=name,
                filepath=filepath,
            )
        )
        session.commit()


def update_generator(generator_id, new_name):
    """
    Update the name of a generator in the database.

    Args:
        generator_id (int): The ID of the generator to update.
        new_name (str): The new name to set for the generator.

    Returns:
        None
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Update the name of the generator in the database
    # cursor.execute(
    #     "UPDATE generators SET name = ? WHERE id = ?", (new_name, generator_id)
    # )

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        generator = (
            session.query(ExperimentGenerators)
            .filter(ExperimentGenerators.id == generator_id)
            .first()
        )
        generator.name = new_name
        session.commit()


def delete_generator(generator_id):
    """
    Delete a generator from the database.

    Args:
        generator_id (int): The ID of the generator.

    Returns:
        None
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Delete the generator from the database
    # cursor.execute("DELETE FROM generators WHERE id = ?", (generator_id,))

    # conn.commit()
    # conn.close()

    with SessionLocal() as session:
        generator = (
            session.query(ExperimentGenerators)
            .filter(ExperimentGenerators.id == generator_id)
            .first()
        )
        session.delete(generator)
        session.commit()


def read_in_generators():
    """
    Read in all generator files from the current generators folder, assigning an id to each one.
    Ignoring this file as well as any files that are already in the database.
    Args:
        None

    Returns:
        None
    """

    # Get the generators folder from the environment variables
    # try:
    #     generators = os.environ["PANDA_SDL_GENERATORS_DIR"]
    # except KeyError as e:
    #     raise ValueError(
    #         "PANDA_SDL_GENERATORS_DIR environment variable not set in .env file."
    #     ) from e

    # Get the generators folder from the config.ini file
    generators = config.get("GENERAL", "generators_dir")

    # Get all files in the generators folder
    generators = os.listdir(generators)

    # Remove any __ files from the list
    generators = [generator for generator in generators if "__" not in generator]

    # remove any non-python files from the list
    generators = [generator for generator in generators if ".py" in generator]

    # Get the current generators from the database
    current_generators = get_generators()

    # Get the current generator ids
    current_generator_ids = [generator.id for generator in current_generators]

    # Get the next generator id
    if current_generator_ids:
        next_generator_id = max(current_generator_ids) + 1
    else:
        next_generator_id = 1

    # Get the filepaths of the current generators
    current_generator_filepaths = [
        generator.filepath for generator in current_generators
    ]

    # Iterate through the generators
    for generator in generators:
        # If the generator is not already in the database
        if generator not in current_generator_filepaths:
            # Insert the generator into the database
            insert_generator(next_generator_id, "", "", generator[:-3], generator)
            next_generator_id += 1
        else:
            # Get the id of the generator
            generator_id = current_generators[
                current_generator_filepaths.index(generator)
            ].id

            # Update the generator in the database
            update_generator(generator_id, generator)

    # Delete any generators that are no longer in the generators folder
    for generator in current_generators:
        if generator.filepath not in generators:
            delete_generator(generator.id)


def get_generator_id(generator_name) -> int:
    """
    Get the id of a generator from the database.

    Args:
        generator_name (str): The name of the generator.

    Returns:
        int: The id of the generator.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get the id of the generator from the database
    # cursor.execute("SELECT id FROM generators WHERE name = ?", (generator_name,))
    # generator_id = cursor.fetchone()[0]

    # conn.close()

    # return generator_id

    with SessionLocal() as session:
        generator = (
            session.query(ExperimentGenerators)
            .filter(ExperimentGenerators.name == generator_name)
            .first()
        )
        return generator.id


def get_generator_name(generator_id) -> str:
    """
    Get the name of a generator from the database.

    Args:
        generator_id (int): The id of the generator.

    Returns:
        str: The name of the generator.
    """
    # conn = sqlite3.connect(SQL_DB_PATH)
    # cursor = conn.cursor()

    # # Get the name of the generator from the database
    # cursor.execute("SELECT name FROM generators WHERE id = ?", (generator_id,))
    # generator_name = cursor.fetchone()[0]

    # conn.close()

    # return generator_name

    with SessionLocal() as session:
        generator = (
            session.query(ExperimentGenerators)
            .filter(ExperimentGenerators.id == generator_id)
            .first()
        )
        return generator.name


def run_generator(generator_id):
    """
    Run a generator.

    Args:
        generator_id (int): The id of the generator to run.

    Returns:
        None
    """
    generator = get_generator_by_id(generator_id)
    print(f"Running generator {generator.name}...")
    generator_module = importlib.import_module(
        f"panda_experiment_generators.{generator.filepath[:-3]}"
    )
    generator_function = getattr(generator_module, "main")
    generator_function()
    print(f"Generator {generator.name} complete.")


# endregion
