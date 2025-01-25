"""
sql_slack_tickets.py
~~~~~~~~~~~~~~~~~~~~
This module contains functions to interact with the slack_tickets table in the database.
The slack_tickets table is used to store slack messages that are waiting to be processed.
"""

from dataclasses import dataclass

from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import SlackTickets


@dataclass
class SlackTicket:
    """
    A dataclass to represent a slack ticket.
    """

    msg_id: str
    channel_id: str
    msg_text: str
    valid_cmd: int
    timestamp: str
    addressed_timestamp: str


def insert_slack_ticket(ticket: SlackTicket) -> None:
    """
    Insert a slack ticket into the slack_tickets table.

    Args:
        ticket (SlackTicket): The slack ticket to insert.
    """

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

    with SessionLocal() as session:
        ticket = (
            session.query(SlackTickets).filter(SlackTickets.msg_id == msg_id).first()
        )
    if not ticket:
        return None
    return SlackTicket(
        msg_id=ticket.msg_id,
        channel_id=ticket.channel_id,
        msg_text=ticket.message,
        valid_cmd=ticket.response,
        timestamp=ticket.timestamp,
        addressed_timestamp=ticket.addressed_timestamp,
    )
