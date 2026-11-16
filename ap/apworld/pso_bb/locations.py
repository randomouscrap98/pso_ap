from BaseClasses import Location

from .items import BASE_ID, GAME

# name -> (offset, region). Placeholder content until real checks are designed.
LOCATIONS: dict[str, tuple[int, str]] = {
    "Forest 1 Cleared": (1, "Forest"),
    "Forest 2 Cleared": (2, "Forest"),
    "Cave 1 Cleared": (10, "Caves"),
}
LOCATION_NAME_TO_ID = {name: BASE_ID + off for name, (off, _) in LOCATIONS.items()}


class PSOBBLocation(Location):
    game = GAME
