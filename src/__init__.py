# -*- coding: utf-8 -*-


""" xFlow """


import sys
import argparse

import core, utils


__author__ = "Jude D'Souza <dsouza_jude@hotmail.com>"
__version_info__ = (0, 1)
__version__ = '.'.join(map(str, __version_info__))


def _get_args():
    ''' Following are the usage options:

    xflow <CONFIG> [-v | --validate]
    xflow <CONFIG> [-c | --configure]
    xflow <CONFIG> [-p | --publish <STREAM> <JSON>]

    '''
    parser = argparse.ArgumentParser(prog='xflow', usage='%(prog)s CONFIG [options]', description='xFlow | A serverless workflow architecture.')
    parser.add_argument('CONFIG', type=str, help='Absolute path to config file')
    parser.add_argument('-v', action='store_true', help='Validates the config file')
    parser.add_argument('-c', action='store_true', help='Configures lambdas, streams and the subscriptions')
    parser.add_argument('-p', type=str, nargs=2, metavar=("<STREAM>","<JSON>"), required=False, help='Publishes json data to a stream')
    return vars(parser.parse_args())


def main():
    args = _get_args()
    config_file = args['CONFIG']
    if not utils.file_exists(config_file):
        print 'File %s does not exist' % (config_file)
        sys.exit(1)

    print 'Validating config'
    try:
        core.Engine.validate_config(config_file)
    except core.ConfigValidationError as ex:
        print 'Invalid config. %s' % (str(ex))
        sys.exit(1)

    print 'Initializing xFlow engine'
    engine = core.Engine(config_file)

    # Configure the lambdas, streams and subscriptions
    if args['c']:
        print 'Setting up lambdas, streams and subscriptions'
        engine.configure()

    # Publish json data to stream
    if args['p']:
        stream = args['p'][0]
        data = args['p'][1]
        if not utils.is_valid_json(data):
            print 'Invalid json provided'
            sys.exit(1)
        print '\nPublishing to stream: %s\n\nData: %s' % (stream, json.dumps(json.loads(data), indent=4))
        engine.publish(stream, data)


if __name__ == '__main__':
    main()
