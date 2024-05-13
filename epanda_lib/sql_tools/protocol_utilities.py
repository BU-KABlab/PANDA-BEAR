"""Utilities for working with protocols in the database."""

from epanda_lib.sql_utilities import (
    ProtocolEntry,
    select_protocols,
    select_protocol_by_id,
    insert_protocol,
    update_protocol,
    delete_protocol,
    read_in_protocols,
    select_protocol_id,
    select_protocol_name,

)


if __name__ == "__main__":
    read_in_protocols()
    protocols_in_db = select_protocols()
    for each_protocol in protocols_in_db:
        print(each_protocol)
