
How to run xFlow for the wordcount workflow
===========================================

- Validate and configure config

```
>> xflow examples/wordcount/wordcount.yaml -v -c
```

- Publish `FileUploaded` event

```bash
>> xflow examples/wordcount/wordcount.yaml -p FileUploaded '{"execution_id":"abc123", "message":"This is a test"}'
```

```
2017-02-27 14:33:21,674 INFO     Validating config
2017-02-27 14:33:21,758 INFO     validation.valid
2017-02-27 14:33:21,758 INFO     Initializing xFlow engine
2017-02-27 14:33:21,774 INFO     Found credentials in shared credentials file: ~/.aws/credentials
2017-02-27 14:33:21,914 INFO     Starting new HTTPS connection (1): iam.amazonaws.com
2017-02-27 14:33:22,902 INFO     Role exists, role=lambda-execute
2017-02-27 14:33:23,040 INFO     Attached policy, policy=arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole, role=lambda-execute
2017-02-27 14:33:23,184 INFO     Attached policy, policy=arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess, role=lambda-execute
2017-02-27 14:33:23,336 INFO     Added inline Policy, role=lambda-execute, policy=AWSLambdaKinesisPublishRole
2017-02-27 14:33:23,531 INFO     AWS Lambda initialized
2017-02-27 14:33:23,555 INFO     AWS Kinesis initialized
2017-02-27 14:33:23,574 INFO     AWS CloudWatchLogs initialized
2017-02-27 14:33:23,574 INFO     Config is valid
2017-02-27 14:33:23,574 INFO

Publishing to stream: FileUploaded

Data: {"execution_id":"abc123", "message":"This is a test"}
2017-02-27 14:33:23,579 INFO     Starting new HTTPS connection (1): kinesis.eu-west-1.amazonaws.com
2017-02-27 14:33:24,259 INFO     Published

```

- Track the workflow's execution id `abc123`

```bash
>> xflow examples/wordcount/wordcount.yaml -t compute_word_count abc123
```

```
2017-02-27 14:34:03,253 INFO     Validating config
2017-02-27 14:34:03,334 INFO     validation.valid
2017-02-27 14:34:03,334 INFO     Initializing xFlow engine
2017-02-27 14:34:03,350 INFO     Found credentials in shared credentials file: ~/.aws/credentials
2017-02-27 14:34:03,441 INFO     Starting new HTTPS connection (1): iam.amazonaws.com
2017-02-27 14:34:03,951 INFO     Role exists, role=lambda-execute
2017-02-27 14:34:04,090 INFO     Attached policy, policy=arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole, role=lambda-execute
2017-02-27 14:34:04,234 INFO     Attached policy, policy=arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess, role=lambda-execute
2017-02-27 14:34:04,385 INFO     Added inline Policy, role=lambda-execute, policy=AWSLambdaKinesisPublishRole
2017-02-27 14:34:04,507 INFO     AWS Lambda initialized
2017-02-27 14:34:04,923 INFO     AWS Kinesis initialized
2017-02-27 14:34:04,992 INFO     AWS CloudWatchLogs initialized
2017-02-27 14:34:04,992 INFO     Config is valid
2017-02-27 14:34:04,992 INFO


Tracking workflow, workflow_id=compute_word_count, execution_id=abc123
2017-02-27 14:34:04,994 INFO     Starting new HTTPS connection (1): logs.eu-west-1.amazonaws.com
{
    "tracking_summary": {
        "execution_path": "FileUploaded ---> FileDownloaded ---> FileParsed ---> FileFiltered ---> FileAggregated ---> FileSummarized",
        "last_received_event": "FileSummarized",
        "subscribers": null
    },
    "events_received": [
        {
            "timestamp": "2017-02-27T14:33:32Z",
            "data": {
                "event_name": "FileUploaded",
                "message": "This is a test",
                "execution_id": "abc123"
            }
        },
        {
            "timestamp": "2017-02-27T14:33:32Z",
            "data": {
                "event_name": "FileDownloaded",
                "contents": "This is a test",
                "execution_id": "abc123"
            }
        },
        {
            "timestamp": "2017-02-27T14:33:35Z",
            "data": {
                "event_name": "FileParsed",
                "words_arr": [
                    "This",
                    "is",
                    "a",
                    "test"
                ],
                "execution_id": "abc123"
            }
        },
        {
            "timestamp": "2017-02-27T14:33:38Z",
            "data": {
                "event_name": "FileFiltered",
                "words_filtered": [
                    "This",
                    "is",
                    "test"
                ],
                "execution_id": "abc123"
            }
        },
        {
            "timestamp": "2017-02-27T14:33:40Z",
            "data": {
                "event_name": "FileAggregated",
                "words_aggregated": {
                    "This": 1,
                    "test": 1,
                    "is": 1
                },
                "execution_id": "abc123"
            }
        },
        {
            "timestamp": "2017-02-27T14:33:43Z",
            "data": {
                "event_name": "FileSummarized",
                "execution_id": "abc123",
                "summary": {
                    "counts": {
                        "This": 1,
                        "test": 1,
                        "is": 1
                    },
                    "total": 3
                }
            }
        }
    ],
    "events_defined": {
        "FileUploaded": "received",
        "FileDownloaded": "received",
        "FileParsed": "received",
        "FileFiltered": "received",
        "FileAggregated": "received",
        "FileSummarized": "received"
    }
}

```
