from panda_lib import labware

# Define the deck slots
DECK_ROWS = "ABCDEF"
DECK_COLUMNS = range(1, 13)
DECK_SLOTS = [f"{row}{col}" for row in DECK_ROWS for col in DECK_COLUMNS]

# Create a labware registry
registry = labware.LabwareRegistry()

# Define the deck
deck = labware.Deck()
deck.slots = {slot: labware.DeckSlot(slot) for slot in DECK_SLOTS}

# Add a well plate to the deck
well_plate = registry.get_definition("standard_96_wellplate")
if not deck.place_labware(well_plate, ["D1"]):
    print("Failed to place well plate on deck")
# Add a vial holder to the deck
vial_holder = registry.get_definition("vial_rack_8")
if not deck.place_labware(vial_holder, ["A1"]):
    print("Failed to place vial holder on deck")
# Print the deck
print(deck)
for slot, deck_slot in deck.slots.items():
    print(f"{slot}: {deck_slot}")
    if deck_slot.occupied:
        print(f"  Labware: {deck_slot.labware_id}")
        print(f"  Position: {deck_slot.position}")
        print(f"  Type: {registry.definitions[deck_slot.labware_id].type}")
        print(f"  Definition: {registry.definitions[deck_slot.labware_id].name}")
    else:
        print("  Empty")
    print()
