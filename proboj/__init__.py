import argparse
import json
import multiprocessing
import pathlib

import colorama

from proboj.game import Game, GameConfig, GameDescription


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    parser.add_argument("games", type=pathlib.Path)
    parser.add_argument("--single", action="store_true")
    parser.add_argument("-v", "--version", action="version", version="ver. 2")
    parser.add_argument("--concurrency", type=int, default=0)
    args = parser.parse_args()

    colorama.init()
    gc = GameConfig(args.config)
    with open(args.games) as f:
        games = json.load(f)

    if not args.concurrency:
        for game in games:
            gd = GameDescription.from_dict(game)
            g = Game(gc, gd)
            g.run()

            if args.single:
                break
    else:
        gobjs = []

        for game in games:
            gd = GameDescription.from_dict(game)
            g = Game(gc, gd)
            gobjs.append(g)

        with multiprocessing.Pool(args.concurrency) as p:
            p.map(run_one, gobjs)


def run_one(game: Game):
    game.run()


if __name__ == "__main__":
    main()
