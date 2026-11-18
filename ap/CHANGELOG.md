# Changelog

User-facing changes for players and testers. `ap/publish_release.py` publishes the Unreleased section as release
notes and moves it under the new version.

## Unreleased

## 0.0.1-pre.1 (2026-11-18)

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
- `/server <host>` forwards the game to a friend's server, so you can play on theirs.

### Options
- New "Quality of Life" option group with **EXP Multiplier** (1-20, whole numbers).

### Settings (host.yaml, `pso_bb_options`)
- `expose_server`: let friends on other computers join your server (off by default: only your computer can
  connect).
- `newserv_config`: use your own newserv `config.json`.

### Server
- Builds for Windows and Linux.
- Only reachable from your own computer unless you turn on `expose_server`.

### Linux
- Lutris installer (`psobb-ap.yml`) for the Tethealla 1.25.13 game client under Wine.
