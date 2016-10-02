import os
import core


def main(config_path):
    engine = core.Engine(config_path)
    engine.setup()


if __name__ == '__main__':
    main()
