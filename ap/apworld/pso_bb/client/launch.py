"""PSOBB client entry point. Must work in stock Archipelago (Kivy) and ArchipelagoLite (TUI):
see ignore/claude/research/aplite-compat.md. No kvui import outside make_gui, logging only, block until exit."""
import asyncio
import logging

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, handle_url_arg, server_loop

from ..items import GAME

logger = logging.getLogger("PSOBB")


class PSOBBCommandProcessor(ClientCommandProcessor):
    pass


class PSOBBContext(CommonContext):
    game = GAME
    items_handling = 0b111  # all items come from the server (newserv grants them)
    command_processor = PSOBBCommandProcessor

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            logger.info("Connected to slot %s", self.auth)
        elif cmd == "ReceivedItems":
            logger.info("Received %d item(s) (total %d)", len(args["items"]), len(self.items_received))

    def make_gui(self):
        from kvui import GameManager  # only reached when the GUI is enabled

        class PSOBBManager(GameManager):
            base_title = "PSOBB Client"
            logging_pairs = [("Client", "Archipelago"), ("PSOBB", "PSOBB")]

        return PSOBBManager


async def main(args) -> None:
    ctx = PSOBBContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
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
