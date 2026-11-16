from typing import TYPE_CHECKING

from BaseClasses import Region

from .locations import LOCATION_NAME_TO_ID, LOCATIONS, PSOBBLocation

if TYPE_CHECKING:
    from .world import PSOBBWorld

ORIGIN = "Pioneer 2"


def create_regions(world: "PSOBBWorld") -> None:
    mw, p = world.multiworld, world.player
    regions = {name: Region(name, p, mw) for name in (ORIGIN, "Forest", "Caves")}
    mw.regions += regions.values()
    for name, (_, region) in LOCATIONS.items():
        r = regions[region]
        r.locations.append(PSOBBLocation(p, name, LOCATION_NAME_TO_ID[name], r))
    regions[ORIGIN].connect(regions["Forest"])
    regions["Forest"].connect(regions["Caves"], rule=lambda state: state.has("Caves Access", p))
    # Placeholder goal: clear the caves.
    victory = PSOBBLocation(p, "Victory", None, regions["Caves"])
    victory.place_locked_item(world.create_event("Victory"))
    regions["Caves"].locations.append(victory)
    mw.completion_condition[p] = lambda state: state.has("Victory", p)
