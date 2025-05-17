"""
SQL Results Module

This module contains functions for querying the database for potentiostat readouts.
It provides a function to query the database for potentiostat readouts
for a given experiment ID and instrument name. The results are returned as a list
of dictionaries containing the readout values.
"""

import json
import logging

from panda_shared.db_setup import SessionLocal as Session
from panda_shared.log_tools import setup_default_logger

from ..panda_models import PotentiostatReadout

logger: logging.Logger = setup_default_logger(log_name="sql_logger")


def query_potentiostat_readouts(experiment_id, instrument_name=None) -> list:
    """
    Query the database for potentiostat readouts for a given experiment ID and instrument name.

    Args:
        experiment_id (int): The experiment ID to query.
        instrument_name (str, optional): The instrument name to query. Defaults to None.

    Returns:
        list: A list of dictionaries containing the readout values.
    """
    with Session() as session:
        if instrument_name:
            readouts = (
                session.query(PotentiostatReadout)
                .filter_by(instrument_name=instrument_name, experiment_id=experiment_id)
                .order_by(PotentiostatReadout.timestamp)
                .all()
            )
        else:
            readouts = (
                session.query(PotentiostatReadout)
                .filter_by(experiment_id=experiment_id)
                .order_by(PotentiostatReadout.timestamp)
                .all()
            )

    # Convert readout values from JSON string to list/dictionary
    result = []
    for readout in readouts:
        readout: PotentiostatReadout
        result.append(
            {
                "id": readout.id,
                "timestamp": readout.timestamp,
                "instrument_name": readout.interface,
                "readout_values": json.loads(readout.readout_values),
            }
        )

    return result
