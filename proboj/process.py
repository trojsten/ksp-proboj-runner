import gzip
import os
import subprocess
from threading import Thread, Lock
from typing import IO


class ProcessEndException(Exception):
    def __init__(self, exit):
        self.exitcode = exit


class Process:
    def __init__(self, command: list[str]):
        self.command = command
        self._died = True
        self._process: subprocess.Popen
        self.logfile: str | None = None
        self._log: IO | None = None
        self.exitcode: int | None = None

    def get_popen_kwargs(self):
        stderr = subprocess.DEVNULL
        if self.logfile:
            self.open_log()
            stderr = subprocess.PIPE

        return {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": stderr,
            "encoding": "utf-8",
        }

    def start(self):
        if self.poll():
            return

        try:
            self._process = subprocess.Popen(
                self.command,
                **self.get_popen_kwargs(),
            )
            self._died = False
        except OSError as e:
            print(f"Error while starting '{self.command}': {e}")
            return

        if self._log:
            self._watchdog = Thread(target=self._stderr_thread)
            self._watchdog.start()

    def poll(self) -> bool:
        if self._died:
            return False

        self._process.poll()
        if self._process.returncode is not None:
            self.exitcode = self._process.returncode
            self._died = True
            return False

        return True

    def send(self, data: str):
        if not self.poll():
            raise ProcessEndException(self.exitcode)

        try:
            self._process.stdin.write(data + "\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            self.poll()

    def read(self) -> str:
        if not self.poll():
            raise ProcessEndException(self.exitcode)

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
            self._process.wait()

    def teardown(self):
        self.close_log()

    def _stderr_thread(self):
        while self.poll():
            line = self._process.stderr.readline()
            if self._log.closed:
                return
            self._log.write(line)

    def open_log(self):
        if not self.logfile:
            return

        if self._log:
            return

        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        self._log = gzip.open(self.logfile, "wt", encoding="utf-8")

    def write_log(self, data: str):
        if self._log:
            self._log.write(data)

    def close_log(self):
        if self._log:
            try:
                self._log.close()
            except IOError:
                pass
