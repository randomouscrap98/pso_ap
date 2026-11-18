"""Runs the installed newserv as a child process: one per seed (its own --data-dir), output to the "Newserv" logger
(the client's Server tab and log file) and to psobb/newserv.log."""
import asyncio
import collections
import logging
import os
import subprocess
import sys

import Utils

from . import newserv, server_install

logger = logging.getLogger("PSOBB")
server_log = logging.getLogger("Newserv")  # top-level name: aplite gives it its own tab

READY_TIMEOUT = 60  # seconds


def log_path() -> str:
    return Utils.user_path("psobb", "newserv.log")


class ServerProcess:
    def __init__(self) -> None:
        self.proc: asyncio.subprocess.Process | None = None
        self.data_dir: str | None = None
        self.reader: asyncio.Task | None = None
        self.stopping = False
        self.warned_external = False
        self.lock = asyncio.Lock()
        self.recent: collections.deque[str] = collections.deque(maxlen=5)  # shown if newserv dies

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def ensure_running(self, data_dir: str, expose: bool, config: str | None) -> bool:
        """Start newserv for this save dir (restarting it if it runs another), unless a newserv we didn't start
        already answers. Returns whether newserv is up."""
        async with self.lock:
            if self.running and self.data_dir == data_dir:
                return True
            if self.running:
                logger.info("Restarting server for a different seed")
                await self._stop()
            elif await newserv.is_up():
                if not self.warned_external:
                    logger.warning("A newserv this client didn't start is already running on %s; using it. "
                                   "Saves go wherever that server keeps them.", newserv.NEWSERV_URL)
                    self.warned_external = True
                return True
            return await self._start(data_dir, expose, config)

    async def _start(self, data_dir: str, expose: bool, config: str | None) -> bool:
        exe = os.path.join(server_install.install_dir(), "newserv.exe" if sys.platform == "win32" else "newserv")
        args = [exe, f"--data-dir={data_dir}"]
        if not expose:
            args.append("--bind-address=127.0.0.1")
        if config:
            args.append(f"--config={config}")
        os.makedirs(data_dir, exist_ok=True)
        self._open_log_file()
        logger.info("Starting server (saves in %s)", data_dir)
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *args, cwd=server_install.install_dir(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            logger.error("Couldn't start the server: %s", e)
            return False
        self.data_dir = data_dir
        self.stopping = False
        self.reader = asyncio.create_task(self._read_output(self.proc))

        for _ in range(READY_TIMEOUT * 2):
            if not self.running:
                return False  # _read_output reports the exit
            if await newserv.is_up():
                logger.info("Server ready")
                return True
            await asyncio.sleep(0.5)
        logger.error("Server didn't become ready within %ds; see the Server tab or %s", READY_TIMEOUT, log_path())
        return False

    def _open_log_file(self) -> None:
        for h in list(server_log.handlers):
            if isinstance(h, logging.FileHandler):
                server_log.removeHandler(h)
                h.close()
        os.makedirs(os.path.dirname(log_path()), exist_ok=True)
        handler = logging.FileHandler(log_path(), mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        server_log.addHandler(handler)
        server_log.setLevel(logging.INFO)

    async def _read_output(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout
        self.recent.clear()
        while line := await proc.stdout.readline():
            text = line.decode("utf-8", errors="replace").rstrip()
            self.recent.append(text)
            server_log.info(text)
        code = await proc.wait()
        if not self.stopping:
            logger.error("Server exited unexpectedly (code %s). Last output:\n%s", code, "\n".join(self.recent))

    async def stop(self) -> None:
        async with self.lock:
            await self._stop()

    async def _stop(self) -> None:
        if not self.running:
            return
        self.stopping = True
        self.proc.terminate()  # newserv saves during play, not at shutdown: nothing is lost
        try:
            await asyncio.wait_for(self.proc.wait(), 5)
        except asyncio.TimeoutError:
            self.proc.kill()
            await self.proc.wait()
        if self.reader:
            await self.reader
        logger.info("Server stopped")
