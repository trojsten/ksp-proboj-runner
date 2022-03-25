import json
import shlex
from datetime import datetime

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


class GameDescription:
    def __init__(
        self, gamefile: str, players: list[str], arguments: str, timeout: float
    ):
        self.gamefile = gamefile
        self.players = players
        self.timeout = timeout
        self.arguments = arguments

    @classmethod
    def from_json(cls, x: str) -> "GameDescription":
        data = json.loads(x)
        return GameDescription(
            data["gamefile"], data["players"], data["args"], float(data["timeout"])
        )


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
        self.server = Server(shlex.split(self.config.server))
        self.players: dict[str, Player] = {}

        for player in self.desc.players:
            if player not in self.config.players:
                raise ValueError(f"player {player} not found in config file.")
            self.players[player] = Player(
                player, shlex.split(self.config.players[player]), self.desc.timeout
            )

    def start(self):
        self.log(self.S_SERVER, "Starting server...")
        self.server.start()
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
        for player in self.players.keys():
            self.players[player].kill()

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
            # TODO: Write to observer
            self.server.send("OK")

        if command[:9] == "TO PLAYER":
            which = command[10:].strip()
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
                self.server.send("DIED\n.")
            except TimeoutError:
                self.log(self.S_PLAYER, f"{which}: Timeouted.")
                self.players[which].kill()
                self.server.send("DIED\n.")

        if command[:11] == "KILL PLAYER":
            which = command[12:].strip()
            self.log(self.S_PLAYER, f"{which}: Killing.")
            self.players[which].kill()
            self.server.send("OK")
