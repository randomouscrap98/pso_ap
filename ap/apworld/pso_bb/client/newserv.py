"""Talks to the local newserv over its HTTP API (HTTPListen in the release config.json)."""
import asyncio
import json
import urllib.request

from Options import FreeText

from ..options import EXPMultiplier, MoneyMultiplier, ServerName

NEWSERV_URL = "http://127.0.0.1:11500"  # mirrored in ap/generate_release.sh (HTTPListen)

# slot_data keys newserv applies with `ap-set` (mirrored in src/ArchipelagoShellCommands.cc) -> the option that
# bounds them, so `/ap_set` accepts the same values as the player yaml
SERVER_SETTINGS = {"exp_multiplier": EXPMultiplier, "money_multiplier": MoneyMultiplier, "server_name": ServerName}


class NewservError(Exception):
    pass


def _request(path: str, body: dict | None = None) -> dict:
    """GET, or POST when there's a body."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(NEWSERV_URL + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:  # newserv puts the reason in a JSON body
        try:
            msg = json.load(e).get("Message", str(e))
        except ValueError:
            msg = str(e)
        raise NewservError(msg) from None
    except OSError as e:
        raise NewservError(f"can't reach newserv at {NEWSERV_URL}: {e}") from None


async def shell(command: str) -> str:
    """Run a newserv shell command; returns its output."""
    return (await asyncio.to_thread(_request, "/y/shell-exec", {"command": command}))["result"]


async def is_up() -> bool:
    """Whether a newserv answers on NEWSERV_URL."""
    try:
        await asyncio.to_thread(_request, "/y/server")
        return True
    except NewservError:
        return False


def parse_setting(key: str, value: str) -> int | str:
    """Validate a `/ap_set` value the way the player yaml would; raises ValueError."""
    option = SERVER_SETTINGS[key]
    if issubclass(option, FreeText):
        option.validate_text(value)
        return value
    try:
        n = int(value)
    except ValueError:
        raise ValueError(f"{key} must be a whole number") from None
    if not option.range_start <= n <= option.range_end:
        raise ValueError(f"{key} must be {option.range_start}-{option.range_end}")
    return n


async def apply_settings(settings: dict) -> list[str]:
    """Push server settings (slot_data with any overrides on top) to newserv; returns newserv's confirmations."""
    return [await shell(f"ap-set {key} {settings[key]}") for key in SERVER_SETTINGS if key in settings]
