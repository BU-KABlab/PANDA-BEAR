"""Go through a reset all well statuses to new"""
import json
from pathlib import Path


def reset_well_statuses():
    """Loop through the well statuses and set them all to new"""
    well_status_file = Path(__file__).parents[0] / "well_status copy.json"
    # input("This will reset all well statuses to new. Press enter to continue.")

    # Confirm that the user wants this
    choice = input(
    "This will reset all well statuses to new. Press enter to continue. Or enter 'n' to cancel: "
    )
    if choice == "n":
        print("Exiting program.")
        return 0
    with open(well_status_file, "r", encoding="UTF-8") as file:
        well_status = json.load(file)
    for catergory in well_status:
        for well in well_status[catergory]:
            well["status"] = "new"
    with open(well_status_file, "w", encoding="UTF-8") as file:
        json.dump(well_status, file, indent=4)


if __name__ == "__main__":
    reset_well_statuses()
