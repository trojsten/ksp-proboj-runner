import time
from queue import Empty, Queue
from threading import Thread

from proboj.process import Process, ProcessEndException


class Player(Process):
    def __init__(self, name: str, command: list[str], timeout: float):
        super().__init__(command)
        self.name = name
        self.timeout = timeout
        self._queue: Queue | None = None
        self._watchdog: Thread | None = None

    def start(self):
        if self.poll():
            return

        super().start()

        self._queue = Queue()
        self._watchdog = Thread(target=self._watchdog)
        self._watchdog.daemon = True
        self._watchdog.start()

    def _watchdog(self):
        while self.poll():
            line = self._process.stdout.readline()
            self._queue.put(line.decode())

    def read(self) -> str:
        if not self.poll():
            raise ProcessEndException()

        start = time.time()
        data = ""
        while True:
            try:
                to = self.timeout - (time.time() - start)
                if to < 0:
                    raise TimeoutError()

                line: str = self._queue.get(timeout=to)

                if line.strip() == ".":
                    break
                data += line
            except Empty:
                pass

        return data
