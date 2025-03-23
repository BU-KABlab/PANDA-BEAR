from labware.deck import Deck, Labware
from labware.labware_definitions import LabwareRegistry

# fetch labware definitions
labware_registry = LabwareRegistry()

# Establish the deck
print("Establishing the deck")
deck = Deck(definition=labware_registry.get_definition("kablab_panda_v2_deck_v1"))

deck.plot_grid(save_path="deck_plot.png")
# Establish and place a wellplate at slot A1 on the Deck
print("Establishing and placing a wellplate at slot D5")
wellplate = Labware(
    name="plate112",
    definition=labware_registry.get_definition("kablab_96_wellplate_150ul"),
)
deck.place_labware(wellplate, "D3", 0)
deck.plot_grid(save_path="deck_plot.png")

# Establish and place vialrack at slot E1 on the Deck
print("Establishing and placing a vialrack at slot A11")
stock_vialrack = Labware(
    name="stock_vialrack",
    definition=labware_registry.get_definition("kablab_8_vialrack_20000ul"),
)

deck.place_labware(stock_vialrack, "C16", 1)
deck.plot_grid(save_path="deck_plot.png")

# Establish and place another vial rack at slot C13
print("Establishing and placing a vialrack at slot C13")
vialrack = Labware(
    name="vialrack",
    definition=labware_registry.get_definition("kablab_8_vialrack_20000ul"),
)

deck.place_labware(vialrack, "C14", 1)
deck.plot_grid(save_path="deck_plot.png")
