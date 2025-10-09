from panda_lib import protocol


def main(
    instructions,
    toolkit,
):
    """
    Main function to run the experiment protocol.
    This function initializes the protocol module to perform the necessary steps
    """
    protocol.transfer(
        source=toolkit.vials["Vial 1"],
        destination=toolkit.wells["Well 1"],
        volume=1000,
    )

    protocol.move_to_and_perform_cv(instructions, toolkit)
    protocol.clear_well()
    protocol.rinse_well(instructions, toolkit)
