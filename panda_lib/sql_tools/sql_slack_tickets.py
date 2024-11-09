"""
sql_slack_tickets.py
~~~~~~~~~~~~~~~~~~~~
This module contains functions to interact with the slack_tickets table in the database.
The slack_tickets table is used to store slack messages that are waiting to be processed.
"""

from dataclasses import dataclass

from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import SlackTickets
# from panda_lib.sql_tools.sql_utilities import (execute_sql_command,
#                                                execute_sql_command_no_return)


# region Slack Tickets
@dataclass
class SlackTicket:
    """
    A dataclass to represent a slack ticket.
    """

    msg_id: str
    channel_id: str
    msg_txt: str
    valid_cmd: int
    timestamp: str
    addressed_timestamp: str


def insert_slack_ticket(ticket: SlackTicket) -> None:
    """
    Insert a slack ticket into the slack_tickets table.

    Args:
        ticket (SlackTicket): The slack ticket to insert.
    """
    # execute_sql_command_no_return(
    #     """
    #     INSERT INTO slack_tickets (
    #         msg_id,
    #         channel_id,
    #         msg_text,
    #         valid_cmd,
    #         timestamp,
    #         addressed_timestamp
    #         )
    #     VALUES (?, ?, ?, ?, ?, ?)
    #     """,
    #     (
    #         ticket.msg_id,
    #         ticket.channel_id,
    #         ticket.msg_text,
    #         ticket.valid_cmd,
    #         ticket.timestamp,
    #         ticket.addressed_timestamp,
    #     ),
    # )

    with SessionLocal() as session:
        session.add(SlackTickets(**ticket.__dict__))
        session.commit()


def select_slack_ticket(msg_id: str) -> SlackTicket:
    """
    Select a slack ticket from the slack_tickets table.

    Args:
        msg_id (str): The message ID of the slack ticket.

    Returns:
        SlackTicket: The slack ticket.
    """
    # result = execute_sql_command(
    #     """
    #     SELECT
    #         msg_id,
    #         channel_id,
    #         msg_text,
    #         valid_cmd,
    #         timestamp,
    #         addressed_timestamp
    #     FROM slack_tickets
    #     WHERE msg_id = ?
    #     """,
    #     (msg_id,),
    # )
    # if result == []:
    #     return None
    # return SlackTicket(*result[0])

    with SessionLocal() as session:
        result = (
            session.query(SlackTickets).filter(SlackTickets.msg_id == msg_id).first()
        )
        if result is None:
            return None
        return SlackTicket(**result.__dict__)


# endregion
