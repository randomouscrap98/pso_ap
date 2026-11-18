from dataclasses import dataclass

from Options import NamedRange, PerGameCommonOptions


class EXPMultiplier(NamedRange):
    """
    Multiplies EXP from enemies in games you create (newserv's BBGlobalEXPMultiplier).
    Whole numbers only: the client can't display fractional EXP correctly.
    Doesn't apply in challenge mode.
    """
    display_name = "EXP Multiplier"
    range_start = 1
    range_end = 20
    default = 1
    special_range_names = {"vanilla": 1}


class MoneyMultiplier(NamedRange):
    """
    Multiplies Meseta from enemy and box drops and from quest rewards. Selling items is unaffected.
    Large drops are capped at 65535 Meseta each.
    """
    display_name = "Money Multiplier"
    range_start = 1
    range_end = 20
    default = 1
    special_range_names = {"vanilla": 1}


@dataclass
class PSOBBOptions(PerGameCommonOptions):
    exp_multiplier: EXPMultiplier
    money_multiplier: MoneyMultiplier
