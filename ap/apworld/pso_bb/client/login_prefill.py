"""Login autofill for singleplayer: saves a login in the game's settings (the registry) so Start Game logs straight
in. Only when no login is saved: the singleplayer server accepts any login, so an existing one (Ephinea, an older
account) works as is and is never replaced. Research: ignore/claude/research/login-prefill.md.

The client keeps its saved login in HKCU\\Software\\SonicTeam\\PSOBB: ACCOUNT (string), ACCOUNT_CHECK (dword, 1 =
remember; with 0 the client clears the other two at startup) and PASSWORD (0x30-byte binary, encrypted with the
client's own Blowfish-style cipher keyed on the account name, whose tables we read from the player's Psobb.exe).
On Windows we write the real registry; under Wine, the prefix's user.reg text file."""
import hashlib
import logging
import os
import struct
import sys
import time

logger = logging.getLogger("Client")

ACCOUNT = PASSWORD = "player"  # any login works on the singleplayer server
REG_PATH = r"Software\SonicTeam\PSOBB"

# Psobb.exe (Tethealla 1.25.13, 59NL) cipher tables: P (0x48 bytes) and S boxes (0x1000), by virtual address, plus
# the SHA-256 of both so another exe is skipped instead of producing a password the client can't read
P_TABLE, S_TABLE = 0x976020, 0x974F20
TABLES_SHA256 = "3d7211533eb45db63b29030c05b9f6c997b95b45ae7ab235df6a68e15e91abed"
M = 0xFFFFFFFF


def _read_va(exe: bytes, va: int, n: int) -> bytes:
    """n bytes at a virtual address of a PE file."""
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    sections, opt_size = struct.unpack_from("<H", exe, pe + 6)[0], struct.unpack_from("<H", exe, pe + 20)[0]
    rva = va - struct.unpack_from("<I", exe, pe + 24 + 28)[0]
    for i in range(sections):
        _, _, sec_va, raw_size, raw_offset = struct.unpack_from("<8sIIII", exe, pe + 24 + opt_size + 40 * i)
        if sec_va <= rva < sec_va + raw_size:
            return exe[raw_offset + rva - sec_va:raw_offset + rva - sec_va + n]
    raise ValueError(f"address {va:#x} isn't in the file")


class Cipher:
    """The client's saved-password cipher: Blowfish key schedule (16 rounds), 4-round 8-byte blocks."""

    def __init__(self, p_raw: bytes, s_raw: bytes, key: bytes):
        self.p = []
        for i in range(18):  # each table dword: low word byte-swapped, high word XOR the swapped low word
            lo, hi = struct.unpack_from("<HH", p_raw, 4 * i)
            lo = ((lo & 0xFF) << 8) | (lo >> 8)
            self.p.append(((hi ^ lo) << 16) | lo)
        self.s = list(struct.unpack("<1024I", s_raw))
        for i in range(18):
            k = 0
            for j in range(4):
                k = (k << 8) | key[(4 * i + j) % len(key)]
            self.p[i] ^= k
        left = right = 0
        for i in range(0, 18, 2):
            left, right = self._encrypt16(left, right)
            self.p[i], self.p[i + 1] = left, right
        for i in range(0, 1024, 2):
            left, right = self._encrypt16(left, right)
            self.s[i], self.s[i + 1] = left, right

    def _f(self, x: int) -> int:
        s = self.s
        return ((((s[x >> 24] + s[256 + ((x >> 16) & 0xFF)]) & M) ^ s[512 + ((x >> 8) & 0xFF)])
                + s[768 + (x & 0xFF)]) & M

    def _encrypt16(self, left: int, right: int) -> tuple[int, int]:
        for i in range(16):
            left ^= self.p[i]
            right ^= self._f(left)
            left, right = right, left
        return right ^ self.p[17], left ^ self.p[16]

    def encrypt(self, data: bytes) -> bytes:
        p, f, out = self.p, self._f, b""
        for o in range(0, len(data), 8):
            d0, d1 = struct.unpack_from("<II", data, o)
            b = d0 ^ p[0]
            e = f(b) ^ p[1] ^ d1
            b ^= f(e) ^ p[2]
            e ^= f(b) ^ p[3]
            out += struct.pack("<II", e ^ p[5], b ^ f(e) ^ p[4])
        return out


def encrypted_password(exe_path: str, account: str, password: str) -> bytes | None:
    """The registry PASSWORD for this login, or None if the exe isn't the client we know."""
    with open(exe_path, "rb") as f:
        exe = f.read()
    try:
        p_raw, s_raw = _read_va(exe, P_TABLE, 0x48), _read_va(exe, S_TABLE, 0x1000)
    except (ValueError, struct.error):
        return None
    if hashlib.sha256(p_raw + s_raw).hexdigest() != TABLES_SHA256:
        return None
    key = account.encode("ascii").ljust(0x30, b"\0")
    return Cipher(p_raw, s_raw, key).encrypt(password.encode("ascii").ljust(0x30, b"\0"))


# --- Wine: user.reg ---

def wine_prefix(game_dir: str) -> str | None:
    """The Wine prefix the game folder is in: the nearest parent with drive_c/ and user.reg (Lutris, Bottles, Proton,
    plain Wine all use this layout). None if the game folder isn't inside a prefix."""
    path = os.path.abspath(game_dir)
    while True:
        if os.path.isdir(os.path.join(path, "drive_c")) and os.path.isfile(os.path.join(path, "user.reg")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def _section_name(line: str) -> str | None:
    """'[Software\\\\SonicTeam\\\\PSOBB] 1731990000' -> 'software\\sonicteam\\psobb' (key names are case-insensitive)."""
    if not line.startswith("[") or "]" not in line:
        return None
    return line[1:line.index("]")].replace("\\\\", "\\").lower()


def _value_name(line: str) -> str | None:
    """'"ACCOUNT"="x"' -> 'account'."""
    if not line.startswith('"'):
        return None
    end = line.find('"=', 1)
    return line[1:end].lower() if end > 0 else None


def _logical_lines(lines: list[str], start: int, end: int) -> list[tuple[int, int]]:
    """(first, last) physical line of each value in lines[start:end]; a value continues while a line ends in '\\'."""
    out, i = [], start
    while i < end:
        j = i
        while j + 1 < end and lines[j].rstrip("\n").endswith("\\"):
            j += 1
        out.append((i, j))
        i = j + 1
    return out


def _unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def read_user_reg(text: str) -> dict[str, str]:
    """The PSOBB key's values, raw (after '='), by lowercase name."""
    lines = text.splitlines(keepends=True)
    start, end = _find_section(lines)
    if start is None:
        return {}
    values = {}
    for first, last in _logical_lines(lines, start + 1, end):
        joined = "".join(lines[k].rstrip("\n").rstrip("\\").strip() for k in range(first, last + 1))
        name = _value_name(joined)
        if name is not None:
            values[name] = joined[joined.find('"=', 1) + 2:]
    return values


def _find_section(lines: list[str]) -> tuple[int | None, int]:
    """(header index, end index) of the PSOBB key, or (None, len)."""
    want = REG_PATH.lower()
    for i, line in enumerate(lines):
        if _section_name(line) == want:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("[")), len(lines))
            return i, end
    return None, len(lines)


def write_user_reg(text: str, account: str, password: bytes) -> str:
    """user.reg text with the three login values set (other values and keys untouched)."""
    new_values = {
        "account_check": '"ACCOUNT_CHECK"=dword:00000001\n',
        "account": f'"ACCOUNT"="{account}"\n',
        "password": '"PASSWORD"=hex:' + ",".join(f"{b:02x}" for b in password) + "\n",
    }
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    start, end = _find_section(lines)
    if start is None:
        reg_name = REG_PATH.replace("\\", "\\\\")
        lines += ["\n", f"[{reg_name}] {int(time.time())}\n"] + list(new_values.values())
        return "".join(lines)
    keep = []
    for first, last in _logical_lines(lines, start + 1, end):
        if _value_name(lines[first]) not in new_values:
            keep += lines[first:last + 1]
    while keep and not keep[-1].strip():  # new values go before the blank line that ends the key
        keep.pop()
    return "".join(lines[:start + 1] + keep + list(new_values.values()) + ["\n"] + lines[end:])


def _has_saved_login(values: dict[str, str]) -> bool:
    """Whether a remembered, non-empty login is saved (raw user.reg values)."""
    remember = values.get("account_check", "").lower() == "dword:00000001"
    account = _unescape(values.get("account", '""').strip('"'))
    return remember and bool(account.strip())


def _wineserver_running() -> bool:
    """Any wineserver (it rewrites user.reg from memory when it exits). Linux only; Flatpak processes count too."""
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return False
    for pid in pids:
        try:
            with open(f"/proc/{pid}/comm") as f:
                if f.read().strip() == "wineserver":
                    return True
        except OSError:
            continue
    return False


def _autofill_wine(game_dir: str, password: bytes) -> None:
    prefix = wine_prefix(game_dir)
    if prefix is None:
        logger.info("Login autofill: couldn't find the Wine prefix your game folder is in; log in with any username "
                    "and password (the server accepts any login in singleplayer).")
        return
    reg = os.path.join(prefix, "user.reg")
    with open(reg, encoding="latin-1", newline="") as f:  # latin-1 round-trips any bytes Wine wrote
        text = f.read()
    if _has_saved_login(read_user_reg(text)):
        return
    tmp = reg + ".ap-tmp"
    with open(tmp, "w", encoding="latin-1", newline="") as f:
        f.write(write_user_reg(text, ACCOUNT, password))
    os.replace(tmp, reg)
    logger.info("Login autofill: saved a login in your game settings; press Start Game on the title menu.")
    if _wineserver_running():
        logger.info("Login autofill: if the game is open, close it and reconnect, or Wine will undo this.")


# --- Windows registry ---

def _autofill_windows(password: bytes) -> None:
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        def get(name: str):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except OSError:
                return None
        if get("ACCOUNT_CHECK") == 1 and str(get("ACCOUNT") or "").strip():
            return
        winreg.SetValueEx(key, "ACCOUNT_CHECK", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ACCOUNT", 0, winreg.REG_SZ, ACCOUNT)
        winreg.SetValueEx(key, "PASSWORD", 0, winreg.REG_BINARY, password)
    logger.info("Login autofill: saved a login in your game settings; press Start Game on the title menu.")


def autofill(game_dir: str) -> None:
    """Save the singleplayer login if none is saved. Never raises: a failure only means typing a login."""
    try:
        password = encrypted_password(os.path.join(game_dir, "Psobb.exe"), ACCOUNT, PASSWORD)
        if password is None:
            logger.info("Login autofill: your Psobb.exe isn't the client this was made for; log in with any username "
                        "and password (the server accepts any login in singleplayer).")
            return
        if sys.platform == "win32":
            _autofill_windows(password)
        else:
            _autofill_wine(game_dir, password)
    except OSError as e:
        logger.warning("Login autofill failed (%s); log in with any username and password.", e)
