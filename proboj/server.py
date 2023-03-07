import os

from proboj.process import Process


class Server(Process):
    def __init__(self, command: list[str], gamedir: str, workdir: str, disable_logs: bool = False):
        super().__init__(command)
        self.logfile = os.path.join(gamedir, "logs", "__server.gz") if not disable_logs else None
        self.workdir = workdir

    def get_popen_kwargs(self):
        kwargs = super().get_popen_kwargs()
        kwargs["cwd"] = self.workdir
        return kwargs
