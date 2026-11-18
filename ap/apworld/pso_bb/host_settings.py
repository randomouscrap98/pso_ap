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

    expose_server: typing.Union[ExposeServer, bool] = False
    newserv_config: typing.Optional[NewservConfig] = None
