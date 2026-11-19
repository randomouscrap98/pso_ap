from dataclasses import dataclass

from Options import Choice, FreeText, NamedRange, PerGameCommonOptions, Range


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


class MagFeeding(Choice):
    """
    How feeding items to your mag raises its stats.
    Simple: each item raises one stat by the same amount at every mag level and form. Monomate/Dimate/Trimate raise POW,
    Monofluid/Difluid/Trifluid raise MIND, Antidote raises DEX, Antiparalysis raises DEF (small/medium/large: 0.4/0.6/0.8
    of a level). Every item also adds a little IQ and synchro; the atomizers add only IQ (Sol), synchro (Moon) or both
    (Star).
    Vanilla: the game's own feeding tables, which give less and less as the mag evolves.
    """
    display_name = "Mag Feeding"
    option_simple = 0
    option_vanilla = 1
    default = 0


class MagFeedMultiplier(Range):
    """
    Multiplies the stat gains of simple mag feeding. A single feeding gives at most 1.27 levels (the game's limit), so
    at 3 every item gives about the same. No effect with vanilla feeding.
    """
    display_name = "Mag Feed Multiplier"
    range_start = 1
    range_end = 3
    default = 1


class ServerName(FreeText):
    """
    The server name shown in the game's menus and messages.
    Up to 15 characters; no "$" (the game uses it for color codes).
    """
    display_name = "Server Name"
    default = "Archipelago"
    max_length = 15  # the game's menu entry holds 16 characters including the terminator (S_MenuItemT::name)

    @classmethod
    def validate_text(cls, text: str) -> None:
        if not text.strip():
            raise ValueError("Server Name can't be empty")
        if len(text) > cls.max_length:
            raise ValueError(f"Server Name must be at most {cls.max_length} characters: {text!r}")
        if "$" in text or any(not c.isprintable() for c in text):
            raise ValueError(f"Server Name can't contain $ or control characters: {text!r}")


@dataclass
class PSOBBOptions(PerGameCommonOptions):
    exp_multiplier: EXPMultiplier
    money_multiplier: MoneyMultiplier
    mag_feeding: MagFeeding
    mag_feed_multiplier: MagFeedMultiplier
    server_name: ServerName
