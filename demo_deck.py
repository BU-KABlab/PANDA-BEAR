from labware import Deck, Labware, LabwareRegistry

# Load labware definitions
registry = LabwareRegistry()
plate = registry.get_definition("kablab_96_wellplate_150ul")

# Create a deck
print("Creating a deck")
deck = Deck(registry.get_definition("kablab_panda_v2_deck_v1"))

new_deck_def = deck.calculate_slots_from_a1(
    x_coordinate=-442.5,
    y_coordinate=-45.5,
)

# Place labware on the deck
print("Establishing and placing a wellplate at slot A1")
deck.place_labware(plate, "A1")

deck.plot_grid(save_path="deck_plot.png")

print("Establishing and placing a wellplate at slot D5")
wellplate = Labware(
    name="plate112",
    definition=registry.get_definition("kablab_96_wellplate_150ul"),
)
deck.place_labware(wellplate, "D3", 0)
deck.plot_grid(save_path="deck_plot.png")

# Establish and place vialrack at slot E1 on the Deck
print("Establishing and placing a vialrack at slot A11")
stock_vialrack = Labware(
    name="stock_vialrack",
    definition=registry.get_definition("kablab_8_vialrack_20000ul"),
)

deck.place_labware(stock_vialrack, "C16", 1)
deck.plot_grid(save_path="deck_plot.png")

# Establish and place another vial rack at slot C13
print("Establishing and placing a vialrack at slot C13")
vialrack = Labware(
    name="vialrack",
    definition=registry.get_definition("kablab_8_vialrack_20000ul"),
)

deck.place_labware(vialrack, "C14", 1)
deck.plot_grid(save_path="deck_plot.png")

# Establish and place a single vial at slot A17 on the Deck
print("Establishing and placing a single vial at slot A17")
vial = Labware(
    name="vial",
    definition=registry.get_definition("kablab_1_vialrack_20000ul"),
)
deck.place_labware(vial, "A17", 1)
deck.plot_grid(save_path="deck_plot.png")
