import gzip
import json
import os.path
import shlex
from datetime import datetime
from typing import IO

from colorama import Back, Fore, Style

from proboj.player import Player
from proboj.process import ProcessEndException
from proboj.server import Server


class GameConfig:
    def __init__(self, file_name):
        with open(file_name) as f:
            data = json.load(f)
            self.server: str = data["server"]
            self.players: dict[str, str] = data["players"]
            self.timeout = data["timeout"]
            if "server_workdir" in data and data["server_workdir"]:
                self.server_workdir = data["server_workdir"]
            else:
                self.server_workdir = ""


class GameDescription:
    def __init__(self, gamefolder: str, players: list[str], arguments: str):
        self.gamefolder = gamefolder
        self.players = players
        self.arguments = arguments

    @classmethod
    def from_dict(cls, data: dict) -> "GameDescription":
        return GameDescription(data["gamefolder"], data["players"], data["args"])


class Game:
    S_SERVER = Back.YELLOW + Fore.BLACK + " SERVER   " + Style.RESET_ALL
    S_OBSERVER = Back.GREEN + Fore.BLACK + " OBSERVER " + Style.RESET_ALL
    S_PLAYER = Back.BLUE + Fore.BLACK + " PLAYER   " + Style.RESET_ALL

    def log(self, *message):
        print(
            Fore.WHITE
            + Style.DIM
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S ")
            + Style.RESET_ALL,
            end="",
        )
        print(*message)

    def __init__(self, config: GameConfig, desc: GameDescription):
        self.config = config
        self.desc = desc
        self.server = Server(shlex.split(self.config.server), self.desc.gamefolder, self.config.server_workdir)
        self.players: dict[str, Player] = {}

        for player in self.desc.players:
            if player not in self.config.players:
                raise ValueError(f"player {player} not found in config file.")
            self.players[player] = Player(
                player,
                shlex.split(self.config.players[player]),
                self.config.timeout,
                self.desc.gamefolder,
            )

        self.observer_file: IO | None = None
        self.score_file: IO | None = None

    def start(self):
        self.log(self.S_SERVER, "Starting server...")
        self.server.start()
        self.log(self.S_SERVER, "Opening game files.")

        os.makedirs(self.desc.gamefolder, exist_ok=True)
        self.observer_file = gzip.open(
            os.path.join(self.desc.gamefolder, "observer.gz"), "w"
        )
        self.score_file = open(os.path.join(self.desc.gamefolder, "score"), "w")

        self.log(self.S_SERVER, "Sending game config to server.")
        self.server.send("CONFIG")
        self.server.send(" ".join(self.players))
        self.server.send(self.desc.arguments)
        self.server.send(".")

        for player in self.players.keys():
            self.log(self.S_PLAYER, f"{player}: Starting...")
            self.players[player].start()

    def mainloop(self):
        while self.server.poll():
            cont = self._read_cmd()
            if not cont:
                break

        self.teardown()

    def teardown(self):
        self.server.kill()
        self.server.teardown()
        for player in self.players.keys():
            self.players[player].kill()
            self.players[player].teardown()

        if self.observer_file:
            try:
                self.observer_file.close()
            except IOError:
                pass

        if self.score_file:
            try:
                self.score_file.close()
            except IOError:
                pass

    def _read_cmd(self) -> bool:
        try:
            command, *data = self.server.read().splitlines()
        except ValueError as e:
            self.log(
                self.S_SERVER,
                Fore.RED + f"Error while reading command from server: {e}",
            )
            return True

        if command == "END":
            self.log(self.S_SERVER, "Game over.")
            for player in self.players.keys():
                self.players[player].kill()
            return False

        if command == "TO OBSERVER":
            data = "\n".join(data)
            self.log(self.S_OBSERVER, f"Sent {len(data)} bytes.")
            self.observer_file.write((data + "\n").encode())
            self.server.send("OK")

        if command == "SCORES":
            self.log(self.S_OBSERVER, "Saved scores.")
            scores = {}
            for line in data:
                player, score = line.split()
                scores[player] = int(score)
            json.dump(scores, self.score_file)
            self.server.send("OK")

        if command[:9] == "TO PLAYER":
            args = command[10:].strip().split(maxsplit=1)
            which = args[0]

            if len(args) == 2:
                self.players[which].write_log(f"---- {args[1]} ----\n")
            else:
                self.players[which].write_log("-" * 20 + "\n")

            data = "\n".join(data)
            try:
                self.players[which].send(data)
                self.players[which].send(".")
                self.log(self.S_PLAYER, f"{which}: Sent {len(data)} bytes.")
                self.server.send("OK")
            except ProcessEndException:
                self.log(self.S_PLAYER, f"{which}: Died.")
                self.server.send("DIED")

        if command[:11] == "READ PLAYER":
            which = command[12:].strip()
            self.log(self.S_PLAYER, f"{which}: Waiting for data...")
            try:
                player_data = self.players[which].read()
                self.log(self.S_PLAYER, f"{which}: Read {len(player_data)} bytes.")
                self.server.send("OK")
                self.server.send(player_data)
                self.server.send(".")
            except ProcessEndException:
                self.log(self.S_PLAYER, f"{which}: Died.")
                self.server.send("DIED")
            except TimeoutError:
                self.log(self.S_PLAYER, f"{which}: Timeouted.")
                self.players[which].kill()
                self.server.send("DIED")

        if command[:11] == "KILL PLAYER":
            which = command[12:].strip()
            self.log(self.S_PLAYER, f"{which}: Killing.")
            self.players[which].kill()
            self.server.send("OK")

        return True

    def run(self):
        self.start()
        self.mainloop()
