import sys
import argparse

import core, utils


def _get_args():
    ''' Following are the usage options:

    xflow <CONFIG> [--dry-run]
    xflow <CONFIG> [-v | --validate]
    xflow <CONFIG> [-c | --configure]
    xflow <CONFIG> [-p | --publish <STREAM> <JSON>]

    '''
    parser = argparse.ArgumentParser(prog='xflow', usage='%(prog)s CONFIG [options]', description='xFlow | A serverless workflow architecture.')
    parser.add_argument('CONFIG', type=str, help='Absolute path to config file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run the program')
    parser.add_argument('-v', action='store_true', help='Validates the config file')
    parser.add_argument('-c', action='store_true', help='Configures lambdas, streams and the subscriptions')
    parser.add_argument('-p', type=str, nargs=2, metavar=("<STREAM>","<JSON>"), required=False, help='Publishes json data to a stream')
    return vars(parser.parse_args())


def main():
    args = _get_args()
    config_path = args['CONFIG']
    if not utils.file_exists(config_path):
        print 'File %s does not exist' % (config_path)
        sys.exit(1)

    print 'Initializing xFlow engine'
    engine = core.Engine(config_path)

    print 'Validating config'
    try:
        engine.validate_config()
    except ConfigValidationError as ex:
        print 'Invalid config. Error: %s' % (str(ex))
        sys.exit(1)

    # Just dry run
    dry_run = False
    if args['dry_run']:
        dry_run = True

    # Configure the lambdas, streams and subscriptions
    if args['c']:
        print 'Setting up lambdas, streams and subscriptions'
        engine.configure(dry_run)

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
