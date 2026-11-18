from collections.abc import Mapping
from typing import Any, ClassVar

from BaseClasses import ItemClassification, Tutorial
from Options import OptionGroup
from worlds.AutoWorld import WebWorld, World

from . import items, locations, options, regions
from .host_settings import PSOBBSettings
from .options import PSOBBOptions


class PSOBBWebWorld(WebWorld):
    theme = "dirt"
    tutorials = [Tutorial("Multiworld Setup Guide", "Setting up PSOBB for Archipelago.", "English",
                          "setup_en.md", "setup/en", ["haloopdy"])]
    option_groups = [
        OptionGroup("Quality of Life", [
            options.EXPMultiplier,
        ]),
    ]


class PSOBBWorld(World):
    """
    Phantasy Star Online Blue Burst, played on a local modded newserv server.
    """

    game = items.GAME
    web = PSOBBWebWorld()
    options_dataclass = PSOBBOptions
    options: PSOBBOptions
    settings: ClassVar[PSOBBSettings]
    settings_key = "pso_bb_options"  # the default derives from the module path (pso_bb.world_options)
    location_name_to_id = locations.LOCATION_NAME_TO_ID
    item_name_to_id = items.ITEM_NAME_TO_ID
    origin_region_name = regions.ORIGIN

    def create_regions(self) -> None:
        regions.create_regions(self)

    def create_item(self, name: str) -> items.PSOBBItem:
        return items.PSOBBItem(name, items.ITEMS[name][1], self.item_name_to_id[name], self.player)

    def create_event(self, name: str) -> items.PSOBBItem:
        return items.PSOBBItem(name, ItemClassification.progression, None, self.player)

    def create_items(self) -> None:
        pool = [self.create_item("Caves Access")]
        n = len(self.multiworld.get_unfilled_locations(self.player))
        pool += [self.create_item(items.FILLER) for _ in range(n - len(pool))]
        self.multiworld.itempool += pool

    def get_filler_item_name(self) -> str:
        return items.FILLER

    def fill_slot_data(self) -> Mapping[str, Any]:
        return {
            "slot_data_version": 1,
            "exp_multiplier": self.options.exp_multiplier.value,
        }
