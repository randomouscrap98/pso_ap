"""host.yaml settings (pso_bb_options): the client's local preferences, not per-seed options."""
import typing

import settings


class PSOBBSettings(settings.Group):
    class Singleplayer(settings.Bool):
        """Playing alone: only this computer can reach your game server, every login uses the same account (so any
        username and password work, and the client saves one in your game settings if none is saved), and Quick play
        makes Solo games. Turn off to play with friends: they can join your server (with /server <your address> in
        their PSOBB client), everyone logs in with their own username, and Quick play makes games others can join."""

    class NewservConfig(settings.OptionalUserFilePath):
        """Use your own newserv config.json instead of the one shipped with the server. It must keep
        "HTTPListen": ["127.0.0.1:11500"] so the client can talk to newserv."""

    class GameDirectory(settings.OptionalUserFolderPath):
        """Your PSOBB game folder (with Psobb.exe and data/). The server needs some of its files, which the client
        copies over. Empty: the client looks in the usual places and asks you if it can't find it."""
        description = "PSOBB game folder (with Psobb.exe)"  # folder browser title: "Select ..."

    singleplayer: typing.Union[Singleplayer, bool] = True
    game_directory: typing.Optional[GameDirectory] = None
    newserv_config: typing.Optional[NewservConfig] = None
