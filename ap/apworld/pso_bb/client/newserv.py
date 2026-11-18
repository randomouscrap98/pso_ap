"""Talks to the local newserv over its HTTP API (HTTPListen in the release config.json)."""
import asyncio
import json
import urllib.request

NEWSERV_URL = "http://127.0.0.1:11500"  # mirrored in ap/generate_release.sh (HTTPListen)

# slot_data keys newserv applies with `ap-set` (mirrored in src/ArchipelagoShellCommands.cc)
SERVER_SETTINGS = ("exp_multiplier", "money_multiplier")


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


async def apply_settings(slot_data: dict) -> list[str]:
    """Push the slot's server settings to newserv; returns newserv's confirmations."""
    return [await shell(f"ap-set {key} {slot_data[key]}") for key in SERVER_SETTINGS if key in slot_data]
