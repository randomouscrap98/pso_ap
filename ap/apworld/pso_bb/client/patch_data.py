"""Copies the game files newserv's BB patch server needs (newserv README: mandatory) from the player's PSOBB folder
into the installed server: data/ map_*.dat, map_*.evt, unitxt_*, data.gsl -> system/patch-bb/data/, then
unitxt_j.prs over unitxt_e.prs (Tethealla's English client). They can't ship with the server (game data)."""
import glob
import logging
import os
import shutil
import sys

logger = logging.getLogger("Client")  # CommonClient's logger: the main tab in Kivy and aplite

PATTERNS = ("map_*.dat", "map_*.evt", "unitxt_*", "data.gsl")
MARKER = "data.gsl"  # present in the server once the copy is done; each server version installs fresh


def candidates() -> list[str]:
    """Where the game usually is: the Lutris installer's prefix, and C:\\PSOBB (install.reg's location)."""
    if sys.platform == "win32":
        return [r"C:\PSOBB"]
    return [os.path.expanduser("~/Games/psobb-archipelago/drive_c/PSOBB")]


def game_data_dir(path: str) -> str | None:
    """The game's data/ folder, given the game folder or data/ itself; None if it isn't a PSOBB folder."""
    for d in (os.path.join(path, "data"), path):
        if os.path.isfile(os.path.join(d, MARKER)):
            return d
    return None


def find_game(configured: str | None) -> str | None:
    """The configured game folder if valid, else the first valid usual location."""
    for path in ([configured] if configured else []) + candidates():
        if game_data_dir(path):
            return path
    return None


def is_copied(server_dir: str) -> bool:
    return os.path.isfile(os.path.join(dest_dir(server_dir), MARKER))


def dest_dir(server_dir: str) -> str:
    return os.path.join(server_dir, "system", "patch-bb", "data")


def copy(game_dir: str, server_dir: str) -> int:
    """Copy the files; returns how many. The marker goes last, so an interrupted copy is redone."""
    src, dest = game_data_dir(game_dir), dest_dir(server_dir)
    assert src
    os.makedirs(dest, exist_ok=True)
    files = {f for p in PATTERNS for f in glob.glob(os.path.join(src, p))}
    marker = os.path.join(src, MARKER)
    for f in files - {marker}:
        shutil.copy2(f, dest)
    shutil.copy2(os.path.join(src, "unitxt_j.prs"), os.path.join(dest, "unitxt_e.prs"))
    shutil.copy2(marker, dest)
    return len(files)
