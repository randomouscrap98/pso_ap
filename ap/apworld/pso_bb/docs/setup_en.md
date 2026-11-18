# Phantasy Star Online Blue Burst Setup Guide

This is an early test build: you can generate a seed and play PSO Blue Burst through the Archipelago client, but checks
and items are placeholders, so nothing is sent or received yet.

## Requirements

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer
- Windows or Linux (macOS isn't supported)
- The Tethealla 1.25.13 English PSO Blue Burst client (below)
- From the [PSOBB Archipelago releases](https://github.com/randomouscrap98/pso_ap/releases): `pso_bb.apworld`, and on
  Linux `psobb-ap.yml`

You don't need to download the server separately: the client downloads the matching one for you.

## Installation

1. Install Archipelago.
2. Install the apworld: double-click `pso_bb.apworld` (or use "Install APWorld" in the Archipelago Launcher).
3. Install the game client:
   - **Linux:** with [Lutris](https://lutris.net), run `lutris -i psobb-ap.yml` (Flatpak:
     `flatpak run net.lutris.Lutris -i psobb-ap.yml`) and accept the defaults. It downloads the client and sets up
     Wine for you.
   - **Windows:** download
     [TethVer12513_English.zip](https://web.archive.org/web/20240402011115id_/https://ragol.org/files/bb/TethVer12513_English.zip),
     extract it to `C:\PSOBB`, and double-click `install.reg` in that folder once.

   Other folders work too; the client asks for the game folder if it isn't where the defaults put it.

## Generating and hosting a game

1. In the Archipelago Launcher, open "Options Creator" (or run "Generate Template Options" and edit the template in
   `Players/Templates`) and make a yaml for Phantasy Star Online Blue Burst.
2. Put the yaml in your Archipelago `Players` folder and run "Generate".
3. Host the generated file (in `output/`) with "Host" in the Launcher. Hosting on archipelago.gg hasn't been tested
   with this apworld yet.

## Playing

1. In the Launcher, open **PSOBB Client** and connect to the game (e.g. `localhost:38281`) with your slot name.
2. The first time, the client says the server isn't installed: type `/install_server` to download it (about 35 MB).
   Already downloaded a server zip/tarball from the releases page? `/install_server <path to file>` installs it.
3. The client copies some files the server needs from your game folder. If it can't find the game, it opens a folder
   browser; pick the folder with `Psobb.exe` in it. You can also type `/game_directory <path>`. It's remembered in
   `host.yaml`.
4. Wait for "Server ready", then start the game (Linux: from Lutris; Windows: `online.exe`, or `Psobb.exe` to skip the
   launcher).
5. Log in with any username and password: the account is created automatically. Each seed has its own saves, so every
   seed starts with fresh characters.

Keep the client open while you play: closing it stops the server.

## Playing with friends (experimental, untested)

The host sets `expose_server: true` (see settings below) and restarts the client. Friends open the PSOBB Client (they
don't need to connect to Archipelago), type `/server <host's address>`, then start their game. The host may need to
forward ports through their router.

## Settings

Under `pso_bb_options` in `host.yaml` (in your Archipelago folder):

- `game_directory`: your PSOBB game folder. Filled in automatically once found.
- `expose_server`: let other computers join your server. Off by default: only your computer can connect.
- `newserv_config`: path to your own newserv `config.json`, for advanced users. It must keep
  `"HTTPListen": ["127.0.0.1:11500"]`.

## Client commands

- `/install_server [path]`: download the server, or install one from a file.
- `/game_directory [path]`: set your game folder (no path opens a folder browser).
- `/server_info`: show the installed server.
- `/server <host>` / `/server off`: play on a friend's server.

## Troubleshooting

The server's output is in the client's "Server" tab and in `psobb/newserv.log` in your Archipelago folder. Include it
(and the client's log from `logs/`) when reporting a problem.
