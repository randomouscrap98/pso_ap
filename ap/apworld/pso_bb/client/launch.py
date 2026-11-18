"""PSOBB client entry point. Must work in stock Archipelago (Kivy) and ArchipelagoLite (TUI):
see ignore/claude/research/aplite-compat.md. No kvui import outside make_gui, logging only, block until exit."""
import asyncio
import logging
import re

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, handle_url_arg, server_loop
from MultiServer import mark_raw
from settings import get_settings

from ..host_settings import PSOBBSettings
from ..items import GAME
from ..world import PSOBBWorld
from . import newserv, patch_data, server_install
from .forwarder import Forwarder
from .server_process import ServerProcess, server_log

logger = logging.getLogger("Client")  # CommonClient's logger: the main tab in Kivy and aplite


class PSOBBCommandProcessor(ClientCommandProcessor):
    ctx: "PSOBBContext"

    def _cmd_server(self, host: str = "") -> bool:
        """Play on a remote newserv: /server <host> forwards the game's 127.0.0.1 ports there. /server off stops."""
        fwd = self.ctx.forwarder
        if not host:
            if fwd.running:
                logger.info("Forwarding to %s", fwd.target)
            else:
                logger.info("Not forwarding. Usage: /server <host> or /server off")
            return True
        coro = fwd.stop() if host.lower() == "off" else fwd.start(host)
        # aplite may call commands from another thread; schedule on the client's loop either way.
        asyncio.run_coroutine_threadsafe(coro, self.ctx.loop)
        return True

    @mark_raw  # raw text: shlex would eat Windows backslashes
    def _cmd_install_server(self, path: str = "") -> bool:
        """Download the PSOBB server for this apworld, or /install_server <path> to install a zip/tarball you have."""
        path = path.strip().strip('"')
        asyncio.run_coroutine_threadsafe(self.ctx.install_server(path or None), self.ctx.loop)
        return True

    @mark_raw  # raw text: shlex would eat Windows backslashes
    def _cmd_game_directory(self, path: str = "") -> bool:
        """Set your PSOBB game folder (the server needs some of its files). No path opens a folder browser."""
        path = path.strip().strip('"')
        asyncio.run_coroutine_threadsafe(self.ctx.set_game_directory(path or None), self.ctx.loop)
        return True

    def _cmd_server_info(self) -> bool:
        """Show the installed PSOBB server."""
        logger.info(server_install.status_message())
        return True


class PSOBBContext(CommonContext):
    game = GAME
    items_handling = 0b111  # all items come from the server (newserv grants them)
    command_processor = PSOBBCommandProcessor

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.loop = asyncio.get_running_loop()
        self.forwarder = Forwarder()
        self.installing = False
        self.newserv_process = ServerProcess()
        self.slot_data: dict | None = None  # set on Connected; the server needs the seed

    async def shutdown(self) -> None:
        await self.newserv_process.stop()
        await self.forwarder.stop()
        await super().shutdown()

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            logger.info("Connected to slot %s", self.auth)
            self.slot_data = args.get("slot_data", {})
            self.start_server_task = asyncio.create_task(self.start_server())
        elif cmd == "ReceivedItems":
            logger.info("Received %d item(s) (total %d)", len(args["items"]), len(self.items_received))

    async def install_server(self, path: str | None) -> None:
        if self.installing:
            logger.info("Server install already in progress")
            return
        self.installing = True
        try:
            logger.info("Installed server at %s", await asyncio.to_thread(server_install.install, path))
        except server_install.InstallError as e:
            logger.error("Server install failed: %s", e)
            return
        finally:
            self.installing = False
        if self.slot_data is not None:
            await self.start_server()

    def save_dir(self) -> str:
        """Per-seed saves: each seed starts with fresh characters."""
        name = re.sub(r"[^\w-]", "_", f"{self.server_seed_name}_T{self.team}_P{self.slot}")
        return Utils.user_path("psobb", "saves", name)

    async def start_server(self) -> None:
        """Make sure newserv runs for this seed, then push the slot's settings to it."""
        if not server_install.is_installed():
            logger.info(server_install.status_message())
            return
        if not patch_data.is_copied(server_install.install_dir()) and not await self.copy_patch_data():
            return
        settings = PSOBBWorld.settings
        config = settings.newserv_config or None
        if await self.newserv_process.ensure_running(self.save_dir(), bool(settings.expose_server), config):
            await self.apply_server_settings(self.slot_data)

    async def copy_patch_data(self) -> bool:
        """Copy the game files the server needs, finding the game folder (or asking for it) first."""
        game = patch_data.find_game(PSOBBWorld.settings.game_directory)
        if game is None:
            logger.info("Couldn't find your PSOBB game folder; pick it in the folder browser.")
            game = await self.browse_game_directory()
            if game is None:
                logger.error("The server needs files from your PSOBB game folder (the one with Psobb.exe and data/). "
                             "Set it with /game_directory <path>, or /game_directory to browse.")
                return False
        self.save_game_directory(game)
        count = await asyncio.to_thread(patch_data.copy, game, server_install.install_dir())
        logger.info("Copied %d game files from %s into the server", count, game)
        return True

    async def browse_game_directory(self) -> str | None:
        path = await asyncio.to_thread(PSOBBSettings.GameDirectory("").browse)
        if path and not patch_data.game_data_dir(path.resolve()):
            logger.error("%s isn't a PSOBB game folder (no data/data.gsl)", path.resolve())
            return None
        return path.resolve() if path else None

    def save_game_directory(self, game: str) -> None:
        """Remember the game folder in host.yaml (pso_bb_options.game_directory)."""
        settings = PSOBBWorld.settings
        if settings.game_directory != game:
            settings.game_directory = PSOBBSettings.GameDirectory(game)
            get_settings().save()
            logger.info("Saved game folder %s to host.yaml", game)

    async def set_game_directory(self, path: str | None) -> None:
        game = await self.browse_game_directory() if path is None else path
        if game is None:
            return
        if not patch_data.game_data_dir(game):
            logger.error("%s isn't a PSOBB game folder (no data/data.gsl)", game)
            return
        self.save_game_directory(game)
        if self.slot_data is not None:  # connected: the server may have been waiting for this
            await self.start_server()

    async def apply_server_settings(self, slot_data: dict) -> None:
        try:
            for line in await newserv.apply_settings(slot_data):
                logger.info("newserv: %s", line)
        except newserv.NewservError as e:
            logger.warning("Couldn't apply settings to newserv (reconnect to retry): %s", e)

    def make_gui(self):
        from kvui import GameManager, UILog  # only reached when the GUI is enabled

        class PSOBBManager(GameManager):
            base_title = "PSOBB Client"

            def build(self):
                container = super().build()
                # Not in logging_pairs: with more than one, Kivy's first tab becomes "All"; server output is noisy
                self.add_client_tab("Server", UILog(server_log))
                return container

        return PSOBBManager


async def main(args) -> None:
    ctx = PSOBBContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    logger.info(server_install.status_message())
    if Utils.gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    await ctx.shutdown()


def launch_client(*args: str) -> None:
    Utils.init_logging("PSOBBClient")
    parser = get_base_parser(description="PSOBB Archipelago client")
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    parsed = handle_url_arg(parser.parse_args(args), parser=parser)
    asyncio.run(main(parsed))
