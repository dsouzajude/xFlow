import time
import json
import logging
import boto3
import botocore

import utils


log = logging.getLogger(__name__)


class MissingSourceCodeFileError(Exception):
    pass


class Lambda(object):

    def __init__(self, region, role_arn,
                 subnet_ids=[], security_group_ids=[],
                 timeout_time=5, aws_access_key_id=None, aws_secret_access_key=None):
        self.role_arn = role_arn
        self.timeout_time = timeout_time
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids
        self.awslambda = boto3.client('lambda', region,
                                      aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)

    def create_or_update_function(self, name, runtime, handler, description=None,
                                  zip_filename=None, s3_filename=None, local_filename=None):
        # TODO: Verify if function code does get updated
        if zip_filename:
            zip_blob = utils.get_zip_contents(zip_filename)
            code = {'ZipFile': zip_blob}
            log.debug('source=zip, file=%s' % zip_filename)
        elif local_filename:
            zip_filename = utils.zip_file(local_filename)
            zip_blob = utils.get_zip_contents(zip_filename)
            code = {'ZipFile': zip_blob}
            log.debug('source=local, file=%s' % local_filename)
        elif s3_filename:
            bucket, key = utils.get_host(s3_filename), utils.get_path(s3_filename)
            code = {'S3Bucket': bucket, 'S3Key': key}
            log.debug('source=s3, file=%s' % s3_filename)
        else:
            log.error('Missing source')
            raise MissingSourceCodeFileError("Must provide either zip_filename, s3_filename or local_filename")

        try:
            if zip_filename or local_filename:
                function = self.awslambda \
                               .update_function_code(FunctionName=name,
                                                     ZipFile=code['ZipFile'],
                                                     Publish=True)
            else:
                function = self.awslambda \
                               .update_function_code(FunctionName=name,
                                                     S3Bucket=code['S3Bucket'],
                                                     S3Key=code['S3Key'],
                                                     Publish=True)
            log.info("Lambda updated, lambda=%s" % name)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                handler = '%s.%s' % (name, handler)
                # Amazon needs a few seconds to replicate the new role through
                # all regions. So creating a Lambda function just after the role
                # creation would sometimes result in botocore.exceptions.ClientError:
                # An error occurred (InvalidParameterValueException) when calling
                # the CreateFunction operation: The role defined for the function
                # cannot be assumed by Lambda.
                lambda_created = False
                last_ex = None
                for i in range(1, 10):
                    try:
                        function = self.awslambda \
                                       .create_function(FunctionName=name,
                                                        Runtime=runtime,
                                                        Role=self.role_arn,
                                                        Handler=handler,
                                                        Description=description or name,
                                                        Timeout=self.timeout_time,
                                                        Publish=True,
                                                        Code=code,
                                                        VpcConfig={
                                                         'SubnetIds': self.subnet_ids,
                                                         'SecurityGroupIds': self.security_group_ids
                                                        })
                        log.info("Lambda created, lambda=%s" % name)
                        lambda_created = True
                        break
                    except botocore.exceptions.ClientError as exx:
                        if exx.response['Error']['Code'] == 'InvalidParameterValueException':
                            log.info('Retrying to create lambda, lambda=%s ...' % name)
                            time.sleep(3)
                            last_ex = exx
                        else:
                            raise exx
                if not lambda_created:
                    raise last_ex
            else:
                raise ex

        function_arn = function['FunctionArn']
        return function_arn

    def subscribe_to_stream(self, function_arn, stream_arn):
        try:
            mapping = self.awslambda \
                          .create_event_source_mapping(EventSourceArn=stream_arn,
                                                       FunctionName=function_arn,
                                                       BatchSize=1,
                                                       StartingPosition='TRIM_HORIZON')
            log.info('Subscription created, stream=%s, function=%s' % (function_arn, stream_arn))
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] != 'ResourceConflictException':
                log.error('Subscription failed, stream=%s, function=%s, error=%s' % (stream_arn, function_arn, str(ex)))
                raise ex


class IAM(object):

    POLICY_LAMBDA_KINESIS_EXECUTION_ROLE = 'arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole'
    POLICY_LAMBDA_KINESIS_PUBLISH_NAME = "AWSLambdaKinesisPublishRole"
    POLICY_LAMBDA_KINESIS_PUBLISH = {
        'Version': '2012-10-17',
        'Statement': [
            {
              "Effect": "Allow",
              "Action": [
                "kinesis:PutRecord"
              ],
              "Resource": "*"
            },
        ]
    }
    POLICY_ASSUME_LAMBDA_ROLE = {
        'Version': '2012-10-17',
        'Statement': {
            'Sid': '',
            'Effect': 'Allow',
            'Principal': {
                'Service': 'lambda.amazonaws.com'
            },
            'Action': 'sts:AssumeRole'
        }
    }

    def __init__(self, region,
                 aws_access_key_id=None, aws_secret_access_key=None):
        self.iam = boto3.client('iam', region,
                                aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key)

    def attach_role_policy(self, role_name, policy_arn):
        self.iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        log.info('Attached policy, policy=%s, role=%s' % (policy_arn, role_name))

    def put_role_policy(self, role_name, policy_name, policy_document):
        self.iam.put_role_policy(RoleName=role_name,
                                 PolicyName=policy_name,
                                 PolicyDocument=policy_document)
        log.info("Added inline Policy, role=%s, policy=%s" % (role_name, policy_name))

    def get_or_create_role(self, role_name='lambda-execute'):
        try:
            role = self.iam.get_role(RoleName=role_name)
            log.info('Role exists, role=%s' % role_name)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchEntity':
                role = self.iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(IAM.POLICY_ASSUME_LAMBDA_ROLE))
                log.info('Role created, role=%s' % role_name)
                self.attach_role_policy(role_name, IAM.POLICY_LAMBDA_KINESIS_EXECUTION_ROLE)
                self.put_role_policy(role_name, IAM.POLICY_LAMBDA_KINESIS_PUBLISH_NAME, json.dumps(IAM.POLICY_LAMBDA_KINESIS_PUBLISH))
            else:
                log.error('Creating role failed, role=%s, error=%s' % (role_name, str(ex)))
                raise ex

        role_arn = role['Role']['Arn']
        return role_arn


class Kinesis(object):

    def __init__(self, region,
                 aws_access_key_id=None, aws_secret_access_key=None):
        self.kinesis = boto3.client('kinesis', region,
                                    aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key)

    def get_or_create_stream(self, name):
        try:
            stream = self.kinesis.describe_stream(StreamName=name)
            log.info('Stream exists, stream=%s' % name)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                self.kinesis.create_stream(StreamName=name, ShardCount=1)
                # Wait until the stream is active
                while True:
                    stream = self.kinesis.describe_stream(StreamName=name)
                    if stream['StreamDescription']['StreamStatus'] == 'CREATING':
                        time.sleep(3)
                    else:
                        log.info('Stream created, stream=%s' % name)
                        break
            else:
                raise ex

        stream_arn = stream['StreamDescription']['StreamARN']
        return stream_arn

    def publish(self, stream_name, data):
        self.kinesis.put_record(StreamName=stream_name, Data=data, PartitionKey=data)
        ## TODO: capture error if stream doesn't exist


class CloudWatchLogs(object):

    def __init__(self, region,
                 aws_access_key_id=None, aws_secret_access_key=None):
        self.logs = boto3.client('logs')

    def create_log_group(self, name):
        try:
            self.logs.create_log_group(logGroupName=name)
            log.info('LogGroup created, log_group=%s' % name)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                log.info('LogGroup exists, log_group=%s' % name)
                raise ex

    
