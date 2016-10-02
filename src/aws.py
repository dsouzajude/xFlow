import time
import json
import boto3
import botocore

import utils


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
        if zip_filename:
            zip_blob = utils.get_zip_contents(zip_filename)
            code = {'ZipFile': zip_blob}
        elif local_file:
            zip_filename = utils.zip_file(local_filename)
            zip_blob = utils.get_zip_contents(zip_filename)
            code = {'ZipFile': zip_blob}
        elif s3_filename:
            bucket, key = utils.get_host(s3_filename), utils.get_path(s3_filename)
            code = {'S3Bucket': bucket, 'S3Key': key}
        else:
            raise MissingSourceCodeError("Must provide either zip_filename, s3_filename or local_filename")

        try:
            function = self.awslambda \
                           .update_function_code(FunctionName=name,
                                                 ZipFile=code.get('ZipFile'),
                                                 S3Bucket=code.get('S3Bucket'),
                                                 S3Key=code.get('S3Key'),
                                                 Publish=True)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
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
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] != 'ResourceConflictException':
                raise ex


class IAM(object):

    POLICY_LAMBDA_KINESIS_EXECUTION_ROLE = 'arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole'
    POLICY_ASSUME_LAMBDA_ROLE = {
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': '',
            'Effect': 'Allow',
            'Principal': {
                'Service': 'lambda.amazonaws.com'
            },
            'Action': 'sts:AssumeRole'
        }]
    }

    def __init__(self, region,
                 aws_access_key_id=None, aws_secret_access_key=None):
        self.iam = boto3.client('iam', region,
                                aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key)

    def get_or_create_role(self, region, role_name='lambda-execute'):
        try:
            role = self.iam.get_role(RoleName=role_name)

        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchEntity':
                role = self.iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(POLICY_ASSUME_LAMBDA_ROLE))
                self.iam.attach_role_policy(RoleName=role_name, PolicyArn=POLICY_LAMBDA_KINESIS_EXECUTION_ROLE)
            else:
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
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                self.kinesis.create_stream(StreamName=name, ShardCount=1)
                # Wait until the stream is active
                while True:
                    stream = self.kinesis.describe_stream(StreamName=name):
                    if stream['StreamDescription']['StreamStatus'] == 'CREATING':
                        time.sleep(3)
                    else:
                        break
            else:
                raise ex

        stream_arn = stream['StreamDescription']['StreamARN']
        return stream_arn
