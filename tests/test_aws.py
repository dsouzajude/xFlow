import json
from datetime import datetime
import nose.tools as nt
from mock import patch, ANY, Mock
import logging

import botocore

from xflow import utils
from xflow.aws import CloudWatchLogs, CloudWatchLogDoesNotExist, \
                CloudWatchStreamDoesNotExist, \
                Kinesis, KinesisStreamDoesNotExist, \
                IAM, Lambda, MissingSourceCodeFileError


class TestLambda(object):

    @patch('xflow.aws.boto3.client')
    def setup(self, client_mock):
        self.llambda = Lambda("eu-west-1", "my-role-arn")

    @patch('xflow.utils.zip_file')
    @patch('xflow.utils.get_zip_contents')
    def test_successfully_creates_function(self, zip_contents_mock, zip_file_mock):
        resonse = {"Error": {"Code": "ResourceNotFoundException", "Message": ""}}
        err = botocore.exceptions.ClientError(resonse, "update_function_code")
        self.llambda.awslambda.update_function_code.side_effect = err
        self.llambda.create_or_update_function("myfunc",
                                               "python2.7",
                                               "myhandler",
                                               local_filename="/mycode.py")
        nt.assert_equals(1, self.llambda.awslambda.create_function.call_count)

    @patch('xflow.utils.zip_file')
    @patch('xflow.utils.get_zip_contents')
    def test_successfully_updates_function(self, zip_contents_mock, zip_file_mock):
        self.llambda.create_or_update_function("myfunc",
                                               "python2.7",
                                               "myhandler",
                                               local_filename="/mycode.py")
        nt.assert_equals(1, self.llambda.awslambda.update_function_code.call_count)

    @nt.raises(MissingSourceCodeFileError)
    def test_raises_error_when_source_code_file_not_provided(self):
        self.llambda.create_or_update_function("myfunc",
                                               "python2.7",
                                               "myhandler")

    def test_successfully_subscribes_to_stream(self):
        self.llambda.subscribe_to_stream("my-function-arn", "my-stream-arn")
        nt.assert_equals(1, self.llambda.awslambda.create_event_source_mapping.call_count)


class TestIAM(object):

    @patch('xflow.aws.boto3.client')
    def setup(self, client_mock):
        self.role = "test-role"
        self.iam = IAM("eu-west-1")

    def test_successfully_gets_role(self):
        self.iam.get_or_create_role(self.role)
        nt.assert_equals(1, self.iam.iam.get_role.call_count)
        nt.assert_equals(2, self.iam.iam.attach_role_policy.call_count)
        nt.assert_equals(1, self.iam.iam.put_role_policy.call_count)

    def test_successfully_creates_role(self):
        resonse = {"Error": {"Code": "NoSuchEntity", "Message": ""}}
        err = botocore.exceptions.ClientError(resonse, "get_role")
        self.iam.iam.get_role.side_effect = err
        self.iam.get_or_create_role(self.role)
        nt.assert_equals(1, self.iam.iam.create_role.call_count)
        nt.assert_equals(2, self.iam.iam.attach_role_policy.call_count)
        nt.assert_equals(1, self.iam.iam.put_role_policy.call_count)


class TestKinesis(object):

    @patch('xflow.aws.boto3.client')
    def setup(self, client_mock):
        self.stream = "test-stream"
        self.kinesis = Kinesis("eu-west-1")

    def test_successfully_gets_stream(self):
        self.kinesis.get_or_create_stream(self.stream)
        nt.assert_equals(1, self.kinesis.kinesis.describe_stream.call_count)

    def test_successfully_creates_stream(self):
        resonse = {"Error": {"Code": "ResourceNotFoundException","Message": ""}}
        err = botocore.exceptions.ClientError(resonse, "describe_stream")
        self.kinesis.kinesis.describe_stream.side_effect = err
        try:
            self.kinesis.get_or_create_stream(self.stream)
        except botocore.exceptions.ClientError:
            pass
        nt.assert_equals(1, self.kinesis.kinesis.create_stream.call_count)

    def test_successfully_publishes_to_stream(self):
        self.kinesis.publish(self.stream, "mydata")
        nt.assert_equals(1, self.kinesis.kinesis.put_record.call_count)

    @nt.raises(KinesisStreamDoesNotExist)
    def test_raises_error_when_stream_does_not_exist(self):
        resonse = {"Error": {"Code": "ResourceNotFoundException","Message": ""}}
        err = botocore.exceptions.ClientError(resonse, "describe_stream")
        self.kinesis.kinesis.put_record.side_effect = err
        self.kinesis.publish(self.stream, "mydata")


class TestCloudWatchLogs(object):

    @patch('xflow.aws.boto3.client')
    def setup(self, client_mock):
        self.log_group = "test_group"
        self.log_stream = "test_stream"
        self.logs = CloudWatchLogs("eu-west-1")

    def test_successfully_creates_log_group(self):
        self.logs.create_log_group(self.log_group)
        nt.assert_equals(1, self.logs.cwlogs.create_log_group.call_count)

    def test_successfully_gets_log_events(self):
        mocked_timestamp = 1476826208 * 1000
        mocked_message = '{"foo": "bar"}'
        mocked_events = {
            "events": [
                {
                    "timestamp": mocked_timestamp,
                    "message": mocked_message
                }
            ],
            "nextForwardToken": None
        }
        self.logs.cwlogs.get_log_events.return_value = mocked_events
        expected = [{
            "timestamp": utils.format_datetime(datetime.fromtimestamp(mocked_timestamp / 1000)),
            "data": json.loads(mocked_message)
        }]
        actual = self.logs.get_log_events(self.log_group, self.log_stream)
        nt.assert_equals(expected, actual)

    @nt.raises(CloudWatchStreamDoesNotExist)
    def test_raises_error_when_stream_does_not_exist(self):
        resonse = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "... stream not found ..."
            }
        }
        err = botocore.exceptions.ClientError(resonse, "get_log_events")
        self.logs.cwlogs.get_log_events.side_effect = err
        self.logs.get_log_events(self.log_group, self.log_stream)

    @nt.raises(CloudWatchLogDoesNotExist)
    def test_raises_error_when_log_does_not_exist(self):
        resonse = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "... group not found ..."
            }
        }
        err = botocore.exceptions.ClientError(resonse, "get_log_events")
        self.logs.cwlogs.get_log_events.side_effect = err
        self.logs.get_log_events(self.log_group, self.log_stream)
