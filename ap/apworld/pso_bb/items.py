from BaseClasses import Item, ItemClassification

GAME = "Phantasy Star Online Blue Burst"
BASE_ID = 0x50_5300_0000  # placeholder id space

# name -> (offset, classification). Placeholder content until real items are designed.
ITEMS: dict[str, tuple[int, ItemClassification]] = {
    "Caves Access": (1, ItemClassification.progression),
    "Monomate": (100, ItemClassification.filler),
}
ITEM_NAME_TO_ID = {name: BASE_ID + off for name, (off, _) in ITEMS.items()}
FILLER = "Monomate"


class PSOBBItem(Item):
    game = GAME
