import utils
from aws import Lambda, Kinesis, IAM


LAMBDA_EXECUTE_ROLE_NAME = 'lambda-execute'


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

        self.lambda = self.setup_lambda(region, role_name, timeout_time,
                                        aws_access_key_id, aws_secret_access_key)
        self.kinesis = self.setup_kinesis(region, aws_access_key_id, aws_secret_access_key)


    def setup_lambda(self, region, role_name, timeout_time, aws_access_key_id, aws_secret_access_key):
        iam = IAM(region,
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)
        role_arn = iam.get_or_create_role(region, role_name=role_name)
        return Lambda(region, role_arn, subnet_ids=[], security_group_ids=[], timeout_time=timeout_time,
                      aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    def setup_kinesis(self, region, aws_access_key_id, aws_secret_access_key):
        return Kinesis(region,
                       aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key)

    def is_s3(source):
        return True if utils.get_scheme(source) == 's3'

    def is_local_file(source):
        return True if utils.get_scheme(source) is None and \
                       not source.endswith('zip') else False

    def is_local_zipfile(source):
        return True if utils.get_scheme(source) is None and \
                       source.endswith('zip') else False

    def setup_lambdas(self):
        lambda_mappings = {}
        lambdas = self.config.get('lambdas', [])
        for l in lambdas:
            s3_filename = zip_filename = local_filename = None
            name, runtime, source, handler, description = l['name'], l['runtime'], l['source'], l['handler'], l['description']

            if is_s3(source):
                s3_filename = source
            if is_local_file(soure):
                local_filename = source
            if is_local_zipfile(source):
                zip_filename = source

            lambda_arn = self.lambda \
                             .create_or_update_function(name, runtime, handler, description=description,
                                                        zip_filename=zip_filename, s3_filename=s3_filename,
                                                        local_filename=local_filename)
            lambda_mappings[name] = lambda_arn
        return lambda_mappings

    def setup_streams_and_subscriptions(self, lambda_mappings):
        stream_mappings = {}
        subscriptions = self.config.get('subscriptions')
        for s in subscriptions:
            event_name = s['name']
            lambda_subscribers = s['subscribers']
            stream_arn = self.kinesis.get_or_create_stream(event_name)
            for lambda_name in lambda_subscribers:
                lambda_arn = lambda_mappings[lambda_name]
                self.lambda.subscribe_to_stream(lambda_arn, stream_arn)

    def configure(self):
        ''' Creates the lambda functions, streams and lambda to stream mappings '''
        lambda_mappings = self.setup_lambdas()
        self.setup_streams_and_subscriptions(lambda_mappings)
