import os
import json
import nose.tools as nt
from mock import patch, ANY, Mock
import logging

import xflow
from xflow import core, utils, aws, tracker
from xflow.core import IAM, Engine, ConfigValidationError, WorkflowDoesNotExist, \
                CloudWatchLogDoesNotExist, CloudWatchStreamDoesNotExist


dir_path = os.path.dirname(os.path.realpath(__file__))
config_dir = dir_path + "/configs"


class TestEngineConfigValidation(object):
    ''' Tests that the config successfully validates for
    correct configs and invalidates for incorrect ones '''

    @nt.raises(ConfigValidationError)
    def test_raises_error_for_invalid_config_01(self):
        ''' Test config is successfully invalidated when
        lambda is not defined in a subscription '''
        config_path = config_dir + "/invalid_missing_lambda.yaml"
        Engine.validate_config(config_path)

    @nt.raises(ConfigValidationError)
    def test_raises_error_for_invalid_config_02(self):
        ''' Test config is successfully invalidated when
        event is not defined in a workflow '''
        config_path = config_dir + "/invalid_missing_event.yaml"
        Engine.validate_config(config_path)

    def test_config_successfully_validates(self):
        ''' Test config is validated for a correct config '''
        config_path = config_dir + "/valid.yaml"
        Engine.validate_config(config_path)
        nt.assert_equals(True, True)


class TestEngineConfiguration(object):
    ''' Tests that lambdas, streams, subscriptions, tracker
    and workflows are correctly setup '''

    @patch('core.Engine.setup_lambda')
    @patch('core.Engine.setup_kinesis')
    @patch('core.Engine.setup_cloud_watch_logs')
    def setup(self, cwlogs_mock, kinesis_mock, lambda_mock):
        config_path = config_dir + "/valid.yaml"
        self.test_config = utils.parse_yaml(utils.read_file(config_path))
        self.engine = Engine(config_path)

    def teardown(self):
        self.engine = None

    def test_lambdas_are_setup(self):
        ''' Tests that aws lambdas are created or updated
        from lambdas defined in the config '''
        lambda_names = [l['name'] for l in self.test_config['lambdas'] or []]
        expected = {name: ANY for name in lambda_names}
        actual = self.engine.setup_lambdas()
        nt.assert_equals(expected, actual)

    def test_streams_and_subscriptions_are_setup(self):
        ''' Tests that streams are created and lambdas
        are subscribed successfully to these streams '''
        lambda_mappings = self.engine.setup_lambdas()
        subscriptions = self.test_config['subscriptions'] or []
        stream_names = [s['event'] for s in subscriptions]
        subscribers = []
        for ss in subscriptions:
            for sb in ss['subscribers'] or []:
                subscribers.append(sb)
        expected = {name: ANY for name in stream_names}
        actual = self.engine.setup_streams_and_subscriptions(lambda_mappings)
        nt.assert_equals(expected, actual)
        nt.assert_equals(len(stream_names), self.engine.kinesis.get_or_create_stream.call_count)
        nt.assert_equals(len(subscribers), self.engine.awslambda.subscribe_to_stream.call_count)

    @patch('utils.write_file')
    @patch('tracker.generate_code')
    def test_tracker_is_setup(self, generate_code_mock, write_mock):
        ''' Tests that the tracker lambda is created along with its
        log group and that it is subscribed to all streams in the workflow '''
        workflow_id = "test_workflow"
        stream_arns = [
            "arn:aws:kinesis:eu-west-1:xxxxxxxxxxxx:stream/TestEvent1",
            "arn:aws:kinesis:eu-west-1:xxxxxxxxxxxx:stream/TestEvent2",
            "arn:aws:kinesis:eu-west-1:xxxxxxxxxxxx:stream/TestEvent3"
        ]
        self.engine.setup_tracker(workflow_id, stream_arns)
        nt.assert_equals(1, self.engine.awslambda.create_or_update_function.call_count)
        nt.assert_equals(len(stream_arns), self.engine.awslambda.subscribe_to_stream.call_count)
        nt.assert_equals(1, self.engine.cwlogs.create_log_group.call_count)

    @patch('utils.write_file')
    @patch('tracker.generate_code')
    def test_workflows_are_setup(self, generate_code_mock, write_mock):
        ''' Tests that all workflows as defined in the config are created along
        with their trackers '''
        lambda_mappings = self.engine.setup_lambdas()
        stream_mappings = self.engine.setup_streams_and_subscriptions(lambda_mappings)
        workflows = self.test_config.get('workflows') or []
        num_workflows = len(workflows)
        self.engine.setup_workflows(stream_mappings)
        num_log_groups_created = self.engine.cwlogs.create_log_group.call_count
        nt.assert_equals(num_workflows, num_log_groups_created)

    @patch('utils.write_file')
    @patch('tracker.generate_code')
    def test_engine_is_successfully_configured(self, generate_code_mock, write_mock):
        ''' Tests that the engine is configurated successfully, i.e. the lambda,
        streams, subscriptions, workflows and their trackers are setup. '''
        num_workflows = len(self.test_config.get('workflows') or [])
        num_lambdas = len(self.test_config.get('lambdas') or [])
        num_trackers = num_workflows
        num_subscriptions = len(self.test_config.get('subscriptions') or [])

        self.engine.configure()
        num_lambdas_created = self.engine.awslambda.create_or_update_function.call_count
        num_streams_created = self.engine.kinesis.get_or_create_stream.call_count
        num_workflows_created = self.engine.cwlogs.create_log_group.call_count

        nt.assert_equals(num_lambdas + num_trackers, num_lambdas_created)
        nt.assert_equals(num_subscriptions, num_streams_created)
        nt.assert_equals(num_workflows, num_workflows_created)


class TestEngineInitialization(object):
    ''' Tests that the engine is successfully initialized '''

    def tests_init_is_successful(self):
        ''' Tests that the engine is successfully initialized i.e.
        awslambda, awskinesis and awscwlogs are setup and initialized '''
        config_path = config_dir + "/valid.yaml"
        core.IAM = core.Lambda = core.Kinesis = core.CloudWatchLogs = Mock()
        engine = core.Engine(config_path)
        nt.assert_not_equals(engine.awslambda, None)
        nt.assert_not_equals(engine.kinesis, None)
        nt.assert_not_equals(engine.cwlogs, None)


class TestEnginePublishing(object):
    ''' Tests publishing to a stream '''

    @patch('core.Engine.setup_lambda')
    @patch('core.Engine.setup_kinesis')
    @patch('core.Engine.setup_cloud_watch_logs')
    def test_publish_is_successful(self, cwlogs_mock, kinesis_mock, lambda_mock):
        ''' Test data is successfully published to a stream '''
        config_path = config_dir + "/valid.yaml"
        engine = Engine(config_path)
        engine.publish("test_stream", "test_data")
        num_publishes = engine.kinesis.publish.call_count
        nt.assert_equals(1, num_publishes)


class TestEngineWorkflowTracking(object):
    ''' Tests workflow tracking '''

    @patch('core.Engine.setup_lambda')
    @patch('core.Engine.setup_kinesis')
    @patch('core.Engine.setup_cloud_watch_logs')
    def setup(self, cwlogs_mock, kinesis_mock, lambda_mock):
        config_path = config_dir + "/valid.yaml"
        self.test_config = utils.parse_yaml(utils.read_file(config_path))
        self.workflow = self.test_config['workflows'][0]
        self.workflow_id = self.workflow['id']
        self.workflow_events = self.workflow['flow']
        self.execution_id = "transaction-id-123"
        self.engine = Engine(config_path)

    def teardown(self):
        self.engine = None

    @nt.raises(WorkflowDoesNotExist)
    def test_raises_error_when_workflow_does_not_exist(self):
        workflow_id = "non-existent"
        self.engine.track(workflow_id, self.execution_id)

    @nt.raises(CloudWatchLogDoesNotExist)
    def test_raises_error_when_cwlog_does_not_exist(self):
        self.engine.cwlogs.get_log_events.side_effect = CloudWatchLogDoesNotExist()
        self.engine.track(self.workflow_id, self.execution_id)

    def test_returns_no_tracking_when_no_execution_id_is_found(self):
        self.engine.cwlogs.get_log_events.side_effect = CloudWatchStreamDoesNotExist()
        workflow_state = {e: core.STATE_UNKNOWN for e in self.workflow_events}
        execution_id = "transaction-id-123"

        expected = {
            "events_defined": workflow_state,
            "events_received": [],
            "tracking_summary": {
                "last_received_event": None,
                "subscribers": [],
                "execution_path": self.engine \
                                      ._generate_execution_path(workflow_state)
            }
        }
        actual = self.engine.track(self.workflow_id, self.execution_id)
        nt.assert_equals(expected, actual)

    def test_workflow_successfully_tracks_on_successful_execution(self):
        # Mock so that all events defined are received (and therefore logged)
        mocked_logged_events = [
            {
                "timestamp": "2016-10-09T23:11:00Z",
                "data": {
                    "event_name": e,
                    "execution_id": self.execution_id
                }

            } for e in self.workflow_events
        ]
        self.engine.cwlogs.get_log_events.return_value = mocked_logged_events

        expected_workflow_state = {e: core.STATE_RECEIVED for e in self.workflow_events}
        expected_last_received_event = self.workflow_events[len(self.workflow_events)-1]
        expected_subscribers = [ss['subscribers'] for ss in self.test_config['subscriptions'] \
                if ss['event'] == expected_last_received_event][0]
        expected = {
            "events_defined": expected_workflow_state,
            "events_received": mocked_logged_events,
            "tracking_summary": {
                "last_received_event": expected_last_received_event,
                "subscribers": expected_subscribers,
                "execution_path": self.engine \
                                      ._generate_execution_path(expected_workflow_state)
            }
        }
        actual = self.engine.track(self.workflow_id, self.execution_id)
        nt.assert_equals(expected, actual)

    def test_workflow_successfully_tracks_on_failed_execution(self):
        # Mock so that all events defined except the last one
        # are received (and therefore logged)
        mocked_logged_events = [
            {
                "timestamp": "2016-10-09T23:11:00Z",
                "data": {
                    "event_name": e,
                    "execution_id": self.execution_id
                }

            } for e in self.workflow_events[:-1] # exclude last event
        ]
        self.engine.cwlogs.get_log_events.return_value = mocked_logged_events

        expected_workflow_state = {e: core.STATE_RECEIVED for e in self.workflow_events[:-1]}
        expected_workflow_state[self.workflow_events[-1:][0]] = core.STATE_UNKNOWN
        expected_last_received_event = self.workflow_events[len(self.workflow_events[:-1])-1]
        expected_subscribers = [ss['subscribers'] for ss in self.test_config['subscriptions'] \
                if ss['event'] == expected_last_received_event][0]
        expected = {
            "events_defined": expected_workflow_state,
            "events_received": mocked_logged_events,
            "tracking_summary": {
                "last_received_event": expected_last_received_event,
                "subscribers": expected_subscribers,
                "execution_path": self.engine \
                                      ._generate_execution_path(expected_workflow_state)
            }
        }
        actual = self.engine.track(self.workflow_id, self.execution_id)
        nt.assert_equals(expected, actual)
