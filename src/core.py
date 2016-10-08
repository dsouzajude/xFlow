import os
import logging
import pykwalify
from pykwalify.core import Core

import utils
from aws import Lambda, Kinesis, IAM


log = logging.getLogger(__name__)

LAMBDA_EXECUTE_ROLE_NAME = 'lambda-execute'


class ConfigValidationError(Exception):
    pass


class Engine(object):
    def __init__(self, config_path):

        contents = utils.read_file(config_path)
        self.config = utils.parse_yaml(contents)

        aws_config = self.config.get('aws', {})
        region = os.environ.get('REGION') or aws_config.get('region')
        vpc_id = os.environ.get('VPC_ID') or aws_config.get('vpc_id')
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID') or aws_config.get('aws_access_key_id')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or aws_config.get('aws_secret_access_key')
        role_name = os.environ.get('LAMBDA_EXECUTION_ROLE_NAME') or aws_config.get('lambda_execution_role_name')

        general_config = self.config.get('general', {})
        timeout_time = int(os.environ.get('LAMBDA_TIMEOUT_TIME') or general_config.get('lambda_timeout_time') or 10)

        log.debug('region=%s, vpc_id=%s, role_name=%s' % (region, vpc_id, role_name))
        log.debug('timeout_time=%s' % timeout_time)
        self.awslambda = self.setup_lambda(region,
                                           role_name,
                                           timeout_time,
                                           aws_access_key_id, aws_secret_access_key)
        self.kinesis = self.setup_kinesis(region, aws_access_key_id, aws_secret_access_key)

    def setup_lambda(self, region, role_name, timeout_time, aws_access_key_id, aws_secret_access_key):
        iam = IAM(region,
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)
        role_arn = iam.get_or_create_role(role_name=role_name)
        awslambda = Lambda(region, role_arn,
                      subnet_ids=[],
                      security_group_ids=[],
                      timeout_time=timeout_time,
                      aws_access_key_id=aws_access_key_id,
                      aws_secret_access_key=aws_secret_access_key)
        log.info('AWS Lambda initialized')
        return awslambda

    def setup_kinesis(self, region, aws_access_key_id, aws_secret_access_key):
        awskinesis = Kinesis(region,
                       aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key)
        log.info('AWS Kinesis initialized')
        return awskinesis

    def setup_lambdas(self):
        log.info('Setting up lambdas')
        lambda_mappings = {}
        lambdas = self.config.get('lambdas', [])
        for l in lambdas:
            s3_filename = zip_filename = local_filename = None
            name, runtime, source, handler, description = l['name'], l['runtime'], l['source'], l['handler'], l['description']

            if utils.is_s3_file(source):
                s3_filename = source
            if utils.is_local_file(source):
                local_filename = source
            if utils.is_local_zip_file(source):
                zip_filename = source

            lambda_arn = self.awslambda \
                             .create_or_update_function(name, runtime, handler, description=description,
                                                        zip_filename=zip_filename, s3_filename=s3_filename,
                                                        local_filename=local_filename)
            lambda_mappings[name] = lambda_arn

        log.info('Setup all lambdas')
        return lambda_mappings

    def setup_streams_and_subscriptions(self, lambda_mappings):
        log.info('Setting up streams and subscriptions')
        stream_mappings = {}
        subscriptions = self.config.get('subscriptions')
        for s in subscriptions:
            event_name = s['event']
            lambda_subscribers = s.get('subscribers') or []
            stream_arn = self.kinesis.get_or_create_stream(event_name)
            for lambda_name in lambda_subscribers:
                lambda_arn = lambda_mappings[lambda_name]
                self.awslambda.subscribe_to_stream(lambda_arn, stream_arn)
        log.info("Setup all streams and subscriptions")

    @staticmethod
    def validate_config(config_file):
        ''' Validates config against the schema
        And also validates the lambdas in the subscriptions are defined
        Raises ConfigValidationError if not valid.
        '''
        c = Core(source_file=config_file, schema_files=["schema.yaml"])
        try:
            config = c.validate(raise_exception=True)
        except pykwalify.errors.SchemaError as ex:
            raise ConfigValidationError(str(ex))

        subscriptions = config.get('subscriptions', [])
        lambdas = config.get('lambdas')
        lambda_names = [l['name'] for l in lambdas]
        for ss in subscriptions:
            subscribers = ss.get('subscribers') or []
            for s in subscribers:
                if s not in lambda_names:
                    raise ConfigValidationError("Lambda not defined for subscriber %s" % s)

    def configure(self):
        ''' Creates the lambda functions, streams and lambda to stream mappings '''
        lambda_mappings = self.setup_lambdas()
        self.setup_streams_and_subscriptions(lambda_mappings)

    def publish(self, stream_name, data):
        self.kinesis.publish(stream_name, data)
        log.debug('publishing, stream=%s, data=%s' % (stream_name, data))
