import os
import json
import logging
import pykwalify
from pykwalify.core import Core

import utils
import tracker
from aws import Lambda, Kinesis, IAM, CloudWatchLogs, \
                CloudWatchLogDoesNotExist, CloudWatchStreamDoesNotExist


log = logging.getLogger(__name__)

LAMBDA_EXECUTE_ROLE_NAME = 'lambda-execute'


class ConfigValidationError(Exception):
    pass


class WorkflowDoesNotExist(Exception):
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
        self.cwlogs = self.setup_cloud_watch_logs(region, aws_access_key_id, aws_secret_access_key)

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

    def setup_cloud_watch_logs(self, region,
                               aws_access_key_id, aws_secret_access_key):
        cwlogs = CloudWatchLogs(region,
                       aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key)
        log.info('AWS CloudWatchLogs initialized')
        return cwlogs

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
            stream_mappings[event_name] = stream_arn
            for lambda_name in lambda_subscribers:
                lambda_arn = lambda_mappings[lambda_name]
                self.awslambda.subscribe_to_stream(lambda_arn, stream_arn)
        log.info("Setup all streams and subscriptions")
        return stream_mappings

    def _generate_log_group_name(self, workflow_id):
        log_group_name = '/xFlow/track/%s' % workflow_id
        return log_group_name

    def _get_subscribers(self, event_name):
        all_subscriptions = self.config.get('subscriptions') or []
        event_subscription = [s for s in all_subscriptions if s['event'] == event_name]
        subscribers = event_subscription[0]['subscribers'] if event_subscription else []
        return subscribers

    def setup_tracker(self, workflow_id, stream_arns):
        ''' The tracker is a lambda function that will subscribe itself to
        every stream in the workflow. Its function is to receive events from
        the stream and log them to CloudWatchLogs for tracking.
        '''
        config_filename = "tracker.cfg"
        tracker_filename = "tracker_%s.py" % workflow_id
        log_group_name = self._generate_log_group_name(workflow_id)

        tracker_name = tracker_filename.split(".py")[0]
        handler = "log"
        runtime = "python2.7"
        description = "A tracker that logs events from streams defined in workflow %s" % workflow_id

        def generate_tracker_config(workflow_id):
            config = json.dumps({
                "workflow_id": workflow_id,
                "log_group_name": log_group_name,
            })
            utils.write_file(config_filename, config)

        # Create lambda and package config information with it
        generate_tracker_config(workflow_id)
        tracker.generate_code(tracker_filename)
        tracker_arn = self.awslambda \
                         .create_or_update_function(tracker_name,
                                                    runtime,
                                                    handler,
                                                    description=description,
                                                    local_filename=tracker_filename,
                                                    otherfiles=[config_filename])
        log.info("Created workflow tracker, tracker=%s, workflow_id=%s" % (tracker_name, workflow_id))

        # Subscribe lambda to streams in the workflow
        for stream_arn in stream_arns:
            self.awslambda.subscribe_to_stream(tracker_arn, stream_arn)
            log.info("Subscribed tracker to stream, tracker=%s, stream=%s" % (tracker_name, utils.get_name_from_arn(stream_arn)))

        # Create log group for lambda to log stream events
        self.cwlogs.create_log_group(log_group_name)
        log.info("Created workflow log group, workflow_id=%s, log_group=%s" % (workflow_id, log_group_name))


    def setup_workflows(self, stream_mappings):
        ''' This will setup and upload a tracker (which is essentially a lambda)
        that will be subscribed to all streams in the workflow. The tracker
        will be named from the `workflow_id`.

        It will also create a CloudWatchLog Group so that the tracker can put
        log events to for every event it receives during workflow execution.
        The log group would be named from the `workflow_id`.

        The same is repeated for every workflow in the configuration.
        '''
        workflows = self.config.get('workflows') or []
        for w in workflows:
            workflow_id = w['id']
            log.info("Setting up workflow, workflow_id=%s" % workflow_id)
            stream_names = w['flow']
            stream_arns = [stream_mappings[name] for name in stream_names]
            self.setup_tracker(workflow_id, stream_arns)
            log.info("Created workflow, workflow_id=%s" % workflow_id)

    @staticmethod
    def validate_config(config_file):
        ''' Validates config against the schema
        And also validates the lambdas in the subscriptions that they are defined
        Raises ConfigValidationError if not valid.
        '''
        c = Core(source_file=config_file, schema_files=["schema.yaml"])
        try:
            config = c.validate(raise_exception=True)
        except pykwalify.errors.SchemaError as ex:
            raise ConfigValidationError(str(ex))

        subscriptions = config.get('subscriptions') or []
        lambdas = config.get('lambdas')
        lambda_names = [l['name'] for l in lambdas]
        subscription_events = []
        for ss in subscriptions:
            event_name = ss['event']
            subscription_events.append(event_name)
            subscribers = ss.get('subscribers') or []
            for s in subscribers:
                if s not in lambda_names:
                    raise ConfigValidationError("Lambda not defined for subscriber %s" % s)

        workflows = config.get('workflows') or []
        for w in workflows:
            workflow_id = w['id']
            events = w.get('flow') or []
            for e in events:
                if e not in subscription_events:
                    raise ConfigValidationError("Event %s not defined in workflow %s" % (e, workflow_id))

    def configure(self):
        ''' Creates the lambda functions, streams and lambda to stream mappings '''
        lambda_mappings = self.setup_lambdas()
        stream_mappings = self.setup_streams_and_subscriptions(lambda_mappings)
        self.setup_workflows(stream_mappings)

    def publish(self, stream_name, data):
        self.kinesis.publish(stream_name, data)
        log.debug('publishing, stream=%s, data=%s' % (stream_name, data))

    def track(self, workflow_id, execution_id):
        ''' Tracks the workflow by printing all the events that were
        processed in the workflow.
        '''
        # Get defined workflow events
        workflows = self.config.get('workflows') or []
        workflow_to_track = [w for w in workflows if w['id'] == workflow_id]
        if not workflow_to_track:
            log.error("Workflow not found, workflow_id=%s" % workflow_id)
            raise WorkflowDoesNotExist("workflow_id=%s" % workflow_id)
        workflow_events = workflow_to_track[0].get("flow") or []
        workflow_events = {e: 'unknown_state' for e in workflow_events}

        # Get events received
        log_group_name = self._generate_log_group_name(workflow_id)
        log_stream_name = tracker.generate_log_stream_name(log_group_name, execution_id)
        logged_events = []
        try:
            logged_events = self.cwlogs.get_log_events(log_group_name, log_stream_name)
        except CloudWatchStreamDoesNotExist as ex:
            log.error("""No executions found, workflow_id=%s,
                      execution_id=%s""" % (workflow_id, execution_id))
            logged_events = []
        except CloudWatchLogDoesNotExist as ex:
            log.error("""Something went wrong, Log group was not created,
                      workflow_id=%s, log_group_name=%s""" % (workflow_id, log_group_name))
            raise ex

        # Summarize state of events
        # The tracker adds the "event_name" when logging to the stream
        for e in logged_events:
            data = e['data']
            event_name = data['event_name']
            if workflow_events.get(event_name):
                workflow_events[event_name] = "received"
            else:
                workflow_events[event_name] = "received_but_unexpected"

        # Identify the last received event in the workflow
        # And all the lambda functions subscribed to that event
        # These would indicate that something might have gone wrong with these
        #   lambdas as they were not able to publish the next events in the workflow
        if logged_events:
            num_logged_events = len(logged_events)
            last_received_event = logged_events[num_logged_events -1]['data']['event_name']
            lambdas_of_last_received_event = self._get_subscribers(last_received_event)
        else:
            last_received_event = None
            lambdas_of_last_received_event = None

        return {
            "events_defined": workflow_events,
            "events_received": logged_events,
            "tracking_summary": {
                "last_received_event": last_received_event,
                "subscribers": lambdas_of_last_received_event
            }
        }
