import os
import inspect
import time
import json
import boto3
import botocore
import base64
from datetime import datetime


TRACKER_CONFIG = "tracker.cfg"


def get_config():
    ''' Config file that contains the `workflow_id` and the `log_group_name`.
    It is a json config and should like the following:
    {
        "workflow_id": <WORKFLOW_ID>,
        "log_group_name": <LOG_GROUP_NAME>
    }
    '''
    with open(TRACKER_CONFIG) as f:
        contents = f.read()
    config = json.loads(contents)
    return config


def get_workflow_id(config):
    return config['workflow_id']


def get_log_group_name(config):
    return config['log_group_name']


def generate_log_stream_name(log_group_name, execution_id):
    return "%s/%s" % (log_group_name, execution_id)


def logkv(message, **kwargs):
    kwargs["message"] = message
    now = datetime.now().strftime("%Y-%m-%dT%H.%M.%SZ")
    print "\t", now, ", ".join(["%s=%s" % (k, v) for k, v in kwargs.items()])


def create_log_stream(logs, log_group, log_stream):
    ''' Creates a log stream if doesn't exist.
    Returns True if log stream was created or already exists.
    Returns False if otherwise.
    '''
    try:
        logs.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        logkv("Log stream created", log_group=log_group, log_stream=log_stream)
    except botocore.exceptions.ClientError as ex:
        if ex.response['Error']['Code'] != "ResourceAlreadyExistsException":
            logkv("ERROR creating log stream", log_group_name=log_group, log_stream_name=log_stream)
            return False
        else:
            logkv("Log stream exists", stream=log_stream)
    return True


def describe_stream(logs, log_group, log_stream):
    stream = logs.describe_log_streams(logGroupName=log_group, logStreamNamePrefix=log_stream)
    return stream['logStreams'][0]


def log_to_stream(logs, log_group, log_stream, token, payload):
    if token:
        logs.put_log_events(logGroupName=log_group,
                            logStreamName=log_stream,
                            logEvents=[{
                                "timestamp": int(round(time.time() * 1000)),
                                "message": payload
                            }],
                            sequenceToken=token)
    else:
        logs.put_log_events(logGroupName=log_group,
                            logStreamName=log_stream,
                            logEvents=[{
                                "timestamp": int(round(time.time() * 1000)),
                                "message": payload
                            }])
    logkv("Logged to stream", log_group=log_group, log_stream=log_stream, payload=payload)


def try_log_to_stream(logs, log_group, log_stream, payload):
    total_retries = 10
    retry_count = 0
    last_ex = None
    logged = False
    while not logged and retry_count <= total_retries:
        s = describe_stream(logs, log_group, log_stream)
        token = s.get('uploadSequenceToken')
        try:
            log_to_stream(logs, log_group, log_stream, token, payload)
            logged = True
        except botocore.exceptions.ClientError as ex:
            last_ex = ex
            if ex.response['Error']['Code'] == ["InvalidSequenceTokenException", "DataAlreadyAcceptedException"]:
                retry_count += 1
                time.sleep(3)
                continue
            else:
                break

    if not logged:
        logkv("ERROR Logging to stream",
              log_group=log_group,
              log_stream=log_stream, payload=payload, error=str(last_ex))


def log(event, context):
    logkv("Running lambda function")
    logkv("Reading config")
    config = get_config()

    workflow_id = get_workflow_id(config)
    log_group = get_log_group_name(config)
    logkv("Successfully read config", workflow_id=workflow_id, log_group=log_group)

    error_count = 0
    logkv("Executing tracker")
    logs = boto3.client('logs')

    logkv("Received event", event=json.dumps(event, indent=2))
    for record in event['Records']:
        event_name = record['eventSourceARN'].split("/")[1]
        payload = base64.b64decode(record['kinesis']['data'])
        logkv("Decoded payload", payload=payload)

        # Handle all sorts of error by logging them
        # So that the tracker keeps moving forward for events in the stream
        try:
            # Extract execution_id. If there is no execution_id, return
            payload = json.loads(payload)
            execution_id = payload.get('execution_id')
            if not execution_id:
                logkv("No execution_id found", workflow_id=workflow_id)
                continue

            # Add event name so it can be logged for tracking
            payload["event_name"] = event_name

            # Get or create log stream from execution_id
            log_stream = generate_log_stream_name(log_group, execution_id)
            ok = create_log_stream(logs, log_group, log_stream)
            if not ok:
                continue

            # Try logging to the stream
            try_log_to_stream(logs, log_group, log_stream, json.dumps(payload))

        except Exception as ex:
            logkv("Error on processing record", error=str(ex), record=payload)
            error_count += 1

    return 'Processed %s records with %s failures.' % (len(event['Records']), error_count)


def generate_code(destination):
    filepath = os.path.abspath(inspect.stack()[0][1])
    with open(filepath) as f:
        contents = f.read()
    with open(destination, 'w') as f:
        f.write(contents)
