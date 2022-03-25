import subprocess


class ProcessEndException(Exception):
    pass


class Process:
    def __init__(self, command: list[str]):
        self.command = command
        self._process: subprocess.Popen | None = None

    def start(self):
        if self.poll():
            return

        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
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
