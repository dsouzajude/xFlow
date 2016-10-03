import os
import argparse

import core


def _get_args():
    parser = argparse.ArgumentParser(description='xFlow | A serverless workflow architecture using AWS Lambda functions and Kinesis')
    parser.add_argument('--file', type=str, required=True, help='Absolute path to config file')
    parser.add_argument('--configure', type=str, required=False, help='Absolute path to config file')
    parser.add_argument('--publish', type=str, required=False, help='Publish data to stream')
    parser.add_argument('--stream', type=str, required=False, help='Stream to publish to')
    return vars(parser.parse_args())

def main():
    args = _get_args()
    config_path = args['file']
    engine = core.Engine(config_path)
    if args.get('configure'):
        engine.configure()
    elif args.get('publish'):
        data = args.get('publish')
        stream = args.get('stream')
        engine.publish(stream, data)


if __name__ == '__main__':
    main()
