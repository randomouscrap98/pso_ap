"""Local TCP forwarder: the Tethealla client always connects to 127.0.0.1 (patch 11000, login 12000), so for a
remote newserv we listen there and pipe to the remote host. newserv's post-login reconnect points the game at the
server's ExternalAddress directly, so only these first hops pass through here."""
import asyncio
import logging

logger = logging.getLogger("Client")  # CommonClient's logger: the main tab in Kivy and aplite

BB_PORTS = (11000, 12000)  # bb-patch, bb-data1


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
        if writer.can_write_eof():
            writer.write_eof()  # pass the half-close along; the other direction may still have data
    except (ConnectionError, OSError):
        writer.close()  # hard failure: tear down so the other pipe ends too


class Forwarder:
    def __init__(self, listen_host: str = "127.0.0.1", ports: tuple[int, ...] = BB_PORTS):
        self.listen_host = listen_host
        self.ports = ports
        self.target: str | None = None
        self.servers: list[asyncio.Server] = []

    @property
    def running(self) -> bool:
        return bool(self.servers)

    async def start(self, target: str) -> None:
        await self.stop()
        self.target = target
        try:
            for port in self.ports:
                server = await asyncio.start_server(
                    lambda r, w, p=port: self._handle(r, w, p), self.listen_host, port)
                self.servers.append(server)
        except OSError as e:
            logger.error("Can't listen on %s: %s (is a local newserv already running?)", self.listen_host, e)
            await self.stop()
            return
        logger.info("Forwarding %s ports %s to %s", self.listen_host,
                    ", ".join(map(str, self.ports)), target)

    async def stop(self) -> None:
        for server in self.servers:
            server.close()  # stop listening; don't wait_closed (3.12+ waits for live game connections)
        if self.servers:
            logger.info("Forwarding stopped")
        self.servers = []

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int) -> None:
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(self.target, port), timeout=10)
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Game connected on port %d but %s:%d is unreachable: %s", port, self.target, port, e)
            writer.close()
            return
        logger.info("Game connected on port %d, forwarding to %s", port, self.target)
        await asyncio.gather(_pipe(reader, remote_writer), _pipe(remote_reader, writer))
        writer.close()
        remote_writer.close()
        logger.info("Game disconnected from port %d", port)
