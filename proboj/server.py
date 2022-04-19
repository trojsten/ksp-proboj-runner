import os

from proboj.process import Process


class Server(Process):
    def __init__(self, command: list[str], gamedir: str):
        super().__init__(command)
        self.logfile = os.path.join(gamedir, "logs", "__server.gz")
