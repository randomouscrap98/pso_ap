"""Downloads/unpacks the newserv build that matches this apworld into Archipelago's user dir.

Release builds carry a stamp (server_release.py, written by ap/generate_release.sh): VERSION, URL_BASE and
FILES = {platform: (archive name, SHA-256, size in bytes)}. Dev builds have no stamp: download is unavailable, but a local file still installs."""
import hashlib
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

import Utils

try:
    from .. import server_release as stamp
except ImportError:
    stamp = None

logger = logging.getLogger("Client")  # CommonClient's logger: the main tab in Kivy and aplite

DEV_VERSION = "dev"
VERSION = stamp.VERSION if stamp else DEV_VERSION
PLATFORM = {"win32": "windows", "linux": "linux"}.get(sys.platform)


class InstallError(Exception):
    pass


def servers_dir() -> str:
    return Utils.user_path("psobb", "server")


def install_dir() -> str:
    """Where this version's server lives (complete installs only: unpacked elsewhere, then renamed here)."""
    return os.path.join(servers_dir(), VERSION)


def is_installed() -> bool:
    return os.path.isdir(install_dir())


def can_download() -> bool:
    return stamp is not None and PLATFORM in stamp.FILES


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "PSOBB-AP-client"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done, next_pct = 0, 10
            while chunk := resp.read(1 << 16):
                out.write(chunk)
                done += len(chunk)
                if total and done * 100 >= next_pct * total:
                    logger.info("Downloading server: %d%%", next_pct)
                    next_pct += 10
    except OSError as e:
        raise InstallError(f"download failed: {e}") from None


def _extract(archive: str, dest: str) -> None:
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as t:
            t.extractall(dest, filter="data")  # rejects paths outside dest, links out, device files
    elif zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            root = os.path.realpath(dest)
            for name in z.namelist():
                if not os.path.realpath(os.path.join(root, name)).startswith(root + os.sep):
                    raise InstallError(f"unsafe path in archive: {name}")
            z.extractall(dest)
    else:
        raise InstallError("not a zip or tar archive")


def install(path: str | None = None) -> str:
    """Install from a local archive, or download this version's release when path is None. Blocking.
    Returns the install dir."""
    if PLATFORM is None:
        raise InstallError(f"no server build for this platform ({sys.platform})")
    if path is None and not can_download():
        raise InstallError("this is a dev build of the apworld: no download; use /install_server <path>")
    expected = stamp.FILES[PLATFORM][1] if can_download() else None  # local files are checked too

    os.makedirs(servers_dir(), exist_ok=True)
    with tempfile.TemporaryDirectory(dir=servers_dir(), prefix=".install-") as tmp:
        if path is None:
            name = stamp.FILES[PLATFORM][0]
            path = os.path.join(tmp, name)
            logger.info("Downloading %s/%s", stamp.URL_BASE, name)
            _download(f"{stamp.URL_BASE}/{name}", path)
        elif not os.path.isfile(path):
            raise InstallError(f"no such file: {path}")
        if expected and _sha256(path) != expected:
            raise InstallError(f"{os.path.basename(path)} doesn't match server {VERSION} (SHA-256 mismatch); "
                               "it's corrupt or a different version")

        unpacked = os.path.join(tmp, "unpacked")
        _extract(path, unpacked)
        # Release archives hold one top folder (PSOBB-AP-newserv/); the server root is whichever has system/
        entries = os.listdir(unpacked)
        root = os.path.join(unpacked, entries[0]) if len(entries) == 1 else unpacked
        if not os.path.isdir(os.path.join(root, "system")):
            raise InstallError("archive doesn't look like a PSOBB AP server (no system/ folder)")

        shutil.rmtree(install_dir(), ignore_errors=True)  # reinstall of the same version
        os.replace(root, install_dir())

    _remove_old_versions()
    return install_dir()


def _remove_old_versions() -> None:
    for name in os.listdir(servers_dir()):
        if name != VERSION and not name.startswith("."):
            try:
                shutil.rmtree(os.path.join(servers_dir(), name))
                logger.info("Removed old server %s", name)
            except OSError as e:  # e.g. still running on Windows
                logger.warning("Couldn't remove old server %s: %s", name, e)


def status_message() -> str:
    if is_installed():
        return f"PSOBB server {VERSION} installed at {install_dir()}"
    if PLATFORM is None:
        return f"No PSOBB server build for this platform ({sys.platform})"
    msg = f"PSOBB server {VERSION} not installed. "
    if can_download():
        size_mb = round(stamp.FILES[PLATFORM][2] / 1e6)
        msg += f"/install_server downloads it (~{size_mb} MB from {stamp.URL_BASE}), or "
    return msg + "/install_server <path> installs a zip/tarball you downloaded."
