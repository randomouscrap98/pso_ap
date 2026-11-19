"""Old seeds' slot_data -> the current format, so the client (and later Universal Tracker) only sees one format.

Rule: bump SLOT_DATA_VERSION on any slot_data change the client or tracker reads (new key, removed/renamed key,
changed meaning), and add a step here. A new key's "added" value is the *old behaviour* (what seeds from before the
key did), not the option's default, so an old seed keeps its meaning. Not needed for apworld-only changes.
Modeled on Animal Crossing's slot_data_upgrade.py; the client is part of this apworld, so the steps are plain Python
(AC keeps them in JSON shared with its C++ client).
"""
import copy
from typing import Any

SLOT_DATA_VERSION = 2

# version -> what changed from the version before it. Ops are applied in this order within a step:
#   renamed: {old key: new key}; remapped: {key: [(old value, new value), ...]}; added: {key: old behaviour};
#   removed: [key, ...]
UPGRADE_STEPS: dict[int, dict[str, Any]] = {
    2: {
        "note": "Mag Feeding + Mag Feed Multiplier (before: the game's own feeding)",
        "added": {"mag_feeding": "vanilla", "mag_feed_multiplier": 1},
    },
}


class SeedTooNew(ValueError):
    pass


def upgrade(slot_data: dict[str, Any]) -> dict[str, Any]:
    """A copy of slot_data in the current format. Raises SeedTooNew for a seed from a newer apworld."""
    out = copy.deepcopy(slot_data)
    version = out.get("slot_data_version", 1)
    if version > SLOT_DATA_VERSION:
        raise SeedTooNew(f"this seed needs a newer PSOBB apworld (slot_data v{version}, this one reads up to "
                         f"v{SLOT_DATA_VERSION})")
    for v in range(version + 1, SLOT_DATA_VERSION + 1):
        step = UPGRADE_STEPS.get(v, {})
        for old, new in step.get("renamed", {}).items():
            if old in out:
                out[new] = out.pop(old)
        for key, pairs in step.get("remapped", {}).items():
            for old, new in pairs:
                if key in out and out[key] == old:
                    out[key] = new
                    break
        for key, value in step.get("added", {}).items():
            out.setdefault(key, copy.deepcopy(value))
        for key in step.get("removed", []):
            out.pop(key, None)
    out["slot_data_version"] = SLOT_DATA_VERSION
    return out
