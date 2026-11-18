"""host.yaml settings (pso_bb_options): the client's local preferences, not per-seed options."""
import typing

import settings


class PSOBBSettings(settings.Group):
    class ExposeServer(settings.Bool):
        """Let other computers join your game server (friends use /server <your address> in their PSOBB client).
        Off: only this computer can connect."""

    class NewservConfig(settings.OptionalUserFilePath):
        """Use your own newserv config.json instead of the one shipped with the server. It must keep
        "HTTPListen": ["127.0.0.1:11500"] so the client can talk to newserv."""

    class GameDirectory(settings.OptionalUserFolderPath):
        """Your PSOBB game folder (with Psobb.exe and data/). The server needs some of its files, which the client
        copies over. Empty: the client looks in the usual places and asks you if it can't find it."""
        description = "PSOBB game folder (with Psobb.exe)"  # folder browser title: "Select ..."

    expose_server: typing.Union[ExposeServer, bool] = False
    game_directory: typing.Optional[GameDirectory] = None
    newserv_config: typing.Optional[NewservConfig] = None
