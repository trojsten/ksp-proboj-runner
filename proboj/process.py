import gzip
import os
import subprocess
from typing import IO


class ProcessEndException(Exception):
    pass


class Process:
    def __init__(self, command: list[str]):
        self.command = command
        self._process: subprocess.Popen | None = None
        self.logfile: str | None = None
        self._log: IO | None = None

    def start(self):
        if self.poll():
            return

        stderr = subprocess.DEVNULL
        if self.logfile:
            self.open_log()
            stderr = self._log

        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            encoding="utf-8",
        )

    def poll(self) -> bool:
        if self._process is None:
            return False

        self._process.poll()
        if self._process.returncode is not None:
            self._process = None
            return False

        return True

    def send(self, data: str):
        if not self.poll():
            raise ProcessEndException()

        self._process.stdin.write(data + "\n")
        self._process.stdin.flush()

    def read(self) -> str:
        if not self.poll():
            raise ProcessEndException()

        data = ""
        while self.poll():
            line: str = self._process.stdout.readline()
            if line.strip() == ".":
                break
            data += line

        return data

    def kill(self):
        if self.poll():
            self._process.kill()

    def teardown(self):
        self.close_log()

    def open_log(self):
        if not self.logfile:
            return

        if self._log:
            return

        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)

        self._log = gzip.open(self.logfile, "w")

    def write_log(self, data: str):
        if self._log:
            self._log.write(data.encode())

    def close_log(self):
        if self._log:
            self._log.close()
