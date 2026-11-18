# Changelog

User-facing changes for players and testers. Prereleases (`ap/publish_release.py`) publish the Unreleased section
as-is: everything since the last real release. For a real release, Unreleased is renamed to the version and
cleaned up, then published with `--final`. The script never edits this file.

## Unreleased

Early test build: the apworld generates and the client runs the server, but checks and items are placeholders
(nothing to play for yet).

### Client
- The client downloads and runs the matching server for you. `/install_server` downloads it from this release
  page (the client tells you when it's needed); `/install_server <path>` installs a zip/tarball you downloaded
  yourself. `/server_info` shows what's installed.
- The server starts when you connect to your slot and stops when you close the client. You no longer run newserv
  yourself.
- Each seed gets its own save folder (`psobb/saves/` in your Archipelago folder), so every seed starts with fresh
  characters.
- Server output appears in a "Server" tab and in `psobb/newserv.log`.
- The client copies the game files the server needs from your PSOBB folder, finding it automatically (Lutris
  install, or `C:\PSOBB`) or asking you with a folder browser. `/game_directory [path]` changes it.
- `/server <host>` forwards the game to a friend's server, so you can play on theirs.
- `/ap_set` changes the EXP and Money multipliers after generation, e.g. `/ap_set exp_multiplier 5`. Changes
  apply right away (even in a game you're already in) and stick for that seed; `/ap_set exp_multiplier default`
  goes back to your yaml's value. `/help` lists all client commands.

### Options
- New "Quality of Life" option group:
  - **EXP Multiplier** (1-20, whole numbers).
  - **Money Multiplier** (1-20): multiplies Meseta from enemy and box drops and from quest rewards. Selling items
    is unaffected. Each drop is capped at 65535 Meseta.

### Settings (host.yaml, `pso_bb_options`)
- `expose_server`: let friends on other computers join your server (off by default: only your computer can
  connect).
- `game_directory`: your PSOBB game folder (filled in automatically once found).
- `newserv_config`: use your own newserv `config.json`.

### Server
- Builds for Windows and Linux, based on the latest upstream newserv.
- Only reachable from your own computer unless you turn on `expose_server`.

### Docs
- Setup guide covering install, generating and hosting, and playing.

### Linux
- Lutris installer (`psobb-ap.yml`) for the Tethealla 1.25.13 game client under Wine.
