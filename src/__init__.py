import os
import argparse

import core


def _get_args():
    parser = argparse.ArgumentParser(description='xFlow | A serverless workflow architecture using AWS Lambda functions and Kinesis')
    parser.add_argument('--file', type=str, required=True, help='Absolute path to config file')
    return vars(parser.parse_args())

def main():
    args = _get_args()
    config_path = args['file']
    engine = core.Engine(config_path)
    engine.setup()


if __name__ == '__main__':
    main()
