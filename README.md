
xFlow
=====
A serverless workflow architecture using AWS Lambda functions and Kinesis.

**THIS PROJECT IS CURRENTLY A WORK IN PROGRESS AND IS NOT INTENDED TO BE USED FOR NOW UNTIL RELEASED**


How it works
============
The concept behind xFlow is to define a workflow which comprises of
a number steps that gets executed to complete a task such that the output
of one step is fed in as the input to the next step - except that instead of the
output being fed in as input, the preceding step publishes an event which is subscribed
by the next step. This way each step is executed independently and can run in parallel.

These steps are AWS Lambda functions and primarily, they should do the following:

- It should be subscribed to listen on certain events
- Do work based on these events
- Optionally emit an output event for other lambda functions to work on

For now, the transport for pub/sub we use is AWS Kinesis, but later we intend
to make this as a plugin that can be used for any pub/sub protocol.

This tool internally creates the AWS Lambda functions and subscribes them to AWS Kinesis.


Creating a sample workflow:
==========================

- Create a config that defines your workflow. For example:

```yaml

general:
  lambda_timeout_time: 3

aws:
  region:
  vpc_id:
  aws_access_key_id:
  aws_secret_access_key:
  lambda_execution_role_name: lambda-execute

lambdas:
  - name: lambda_file_reader
    description: Downloads the file and publishes `FileDownloaded` event with the contents in it.
    source: s3://flows/word_count/reader.py.zip
    handler: read_file
    runtime: python2.7
  - name: lambda_parser
    description: Reads contents, parses it into an array of words and publishes a `FileParsed` event with the data in it.
    source: s3://flows/word_count/parser.py.zip
    handler: parse
    runtime: python2.7
  - name: lambda_combiner
    description: Groups similar words and aggregates the count and publishes a `FileAggregated` with the grouping in it.
    source: s3://flows/word_count/combiner.py.zip
    handler: parse
    runtime: python2.7
  - name: lambda_filter
    description: Filters out non-words and publishes a 'FileFiltered' with the remainder words in it.
    source: s3://flows/word_count/filter.py.zip
    handler: filter
    runtime: python2.7
  - name: lambda_summarize
    description: Outputs the word count for every unique word and total words in the file.
    source: git://project/blob/master/flows/word_count/summary.py
    handler: summarize
    runtime: python2.7

subscriptions:
  - name: FileUploaded
    subscribers:
      - lambda_file_reader
  - name: FileDownloaded
    subscribers:
      - lambda_parser
  - name: FileParsed
    subscribers:
      - lambda_combiner
  - name: FileAggregated
    subscribers:
      - lambda_filter
  - name: FileFiltered
    subscribers:
      - lambda_summarize

```

- Setup the workflow via the following command:

  `xflow setup -file word_count.cfg`

  Behind the scenes, this will do the following:
  - Create (or update) AWS Lambda functions.
  - For each lambda function, subscribe them to AWS Kinesis based on the events they are listening for.
  - Lambda functions will be executed once an event is published to AWS Kinesis.

- Tracking the workflow is done via the following command:

  `xflow track -flow word_count -execution_id 112233`

  An instance of a particular workflow is tracked via its `execution_id`. Therefore all events defined
  in a workflow must contain this field. Since it is required to have the events defined in order it
  will then be easy to determine which events were successfully processed and which were not at any
  particular time in the last 7 days.

  The goal of the tracker is to return the state of all events in the workflow given as input
  the `workflow_id` and its `execution_id`. The state would indicate whether the event was processed or not.
  It will then grab the last unprocessed event and fetch all logs for its subscribers (the lambdas) that failed
  to process that event.

  For this to work, there would be a separate tracker for every workflow defined. The tracker would subscribe
  itself to every stream in that workflow and hence it would receive events published to that stream. The tracker itself would be a lambda function and its name would be `tracker_<workflow_id>`. Hence it will be invoked on every
  successful publishing of an event to the stream.

  The actual tracking is done via AWS CloudWatchLogs. For every workflow a CloudWatch `LogGroup` is created. And for every instance of a workflow execution, a `LogStream` would be created.

  Hence, when an event is published to a stream, the tracker would receive the event and extract the
  `execution_id`. It will create a new log stream from this execution_id if not already created. It will
  then store the event in that stream. Since the lambda's name is generated from the workflow_id, it is also
  easy to extract the log group for the log stream.

  For every subsequent event published to the kinesis stream, the corresponding lambda for the workflow will be invoked and it will save the event to the log stream.



xFlow Requirements (and roadmap):
=================================
- Integration with github (so we can download the lambda function from there given the link)
- Lambda functions can subscribe to events
- Lambda functions can publish events
- Monitoring around lambda functions
- Centralized Logging (or ability to route logs) to log server
- Tracking execution in a workflow (via unique `execution_id` which is common to all steps in the workflow)
- CI/ CD for lambda functions
