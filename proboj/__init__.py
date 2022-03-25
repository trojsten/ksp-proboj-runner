import colorama

from proboj.game import Game, GameConfig, GameDescription


def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument("config")
    colorama.init()
    gc = GameConfig("../config.json")
    gd = GameDescription("test", ["test", "test2"], "", 15)
    g = Game(gc, gd)

    g.start()
    g.mainloop()


if __name__ == "__main__":
    main()
