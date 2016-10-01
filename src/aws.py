import json
import boto3
import botocore

class Lambda(object):

    def create_lambda(self):
        pass

    def add_permission(self):
        ''' Adds permission for Kinesis to invoke lambda function '''
        pass


class IAM(object):

    ASSUME_LAMBDA_ROLE_POLICY = {
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

    def create_role(self, role_name='lambda-execute'):
        iam = boto3.client('iam')
        try:
            role = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(ASSUME_LAMBDA_ROLE_POLICY))
            role_arn = role['Role']['Arn']
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'EntityAlreadyExists':
                role = iam.get_role(RoleName=role_name)
                role_arn = role['Role']['Arn']
            else:
                raise ex
        return role_arn


class Kinesis(object):

    def subscribe(self):
        pass

    def add_permission(self):
        ''' Also adds permission for Lambda function to publish to Kinesis '''
        pass
