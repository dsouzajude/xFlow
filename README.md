
xFlow
=====
A serverless workflow architecture using AWS Lambda functions and Kinesis.


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

xFlow uses AWS Kinesis as the streaming engine to publish and subscribe events in a workflow.
As described above, these events would then be processed via AWS Lambda functions after they
have been subscribed to it. The configuration file that you provide to xFlow would be the glue
that combines events to the processors in a workflow.

xFlow will internally create the AWS Lambda functions and subscribe them to AWS Kinesis.
All you need to do is write the body of the lambda functions.

xFlow supports all languages AWS Lambda supports. At this moment, lambdas can only be
uploaded from the local filesystem or s3. In the future we will support integration with
github.


Creating a sample workflow:
==========================

- Create a config that defines your workflow. For example:

```yaml

general:
  lambda_timeout_time: 3

aws:
  region:
  subnet_ids:
  security_group_ids:
  lambda_execution_role_name: lambda-execute

lambdas:
  - name: lambda_reader
    description: Reads contents of a file that was uploaded and publishes those contents.
    source: /xFlow/examples/wordcount/lambda_reader.py
    handler: read
    runtime: python2.7

  - name: lambda_parser
    description: Reads contents, parses it into an array of words.
    source: s3://xFlow/flows/wordcount/lambda_parser.py
    handler: parse
    runtime: python2.7

  - name: lambda_filter
    description: Filters non-letters from words and non-words.
    source: /xFlow/examples/wordcount/lambda_filter.py
    handler: filter_out_non_words
    runtime: python2.7

  - name: lambda_aggregator
    description: Groups similar words and counts them.
    source: /xFlow/examples/wordcount/lambda_aggregator.py
    handler: aggregate
    runtime: python2.7

  - name: lambda_summarizer
    description: Prints unique word counts.
    source: /xFlow/examples/wordcount/lambda_summarizer.py
    handler: summarize
    runtime: python2.7

subscriptions:
  - event: FileUploaded
    subscribers:
      - lambda_reader
  - event: FileDownloaded
    subscribers:
      - lambda_parser
  - event: FileParsed
    subscribers:
      - lambda_filter
  - event: FileFiltered
    subscribers:
      - lambda_aggregator
  - event: FileAggregated
    subscribers:
      - lambda_summarizer
  - event: FileSummarized
    subscribers:

# Optional - Can be used to track a complete workflow
workflows:
  - id: compute_word_count
    flow:
      - FileUploaded
      - FileDownloaded
      - FileParsed
      - FileFiltered
      - FileAggregated
      - FileSummarized
```

- Setup the workflow via the following command:

  `xflow word_count.cfg --configure`

  Behind the scenes, this will do the following:
  - Create (or update) AWS Lambda functions.
  - For each lambda function, subscribe them to AWS Kinesis based on the events they are listening for.
  - Lambda functions will be executed once an event is published to AWS Kinesis.

- Tracking the workflow is done via the following command:

  `xflow word_count.cfg --track <WORKFLOW_ID> <EXECUTION_ID>`

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

- Running in server mode:

  `xflow word_count.cfg --server`

  This will run xflow via server mode. On startup, the server will setup the necessary streams, lambda functions and workflows. You can then publish events to a stream or track workflow executions in a RESTful way. Following are examples how you would do this.

  Publishing:

  `curl -XPOST localhost/publish -d '{"stream":"FileUploaded", "event":{"execution_id":"ex1", "message":"Test with ccc"}}'`

  Tracking:

  `curl -v localhost/track/workflows/compute_word_count/executions/ex1`


xFlow Requirements (and roadmap):
=================================
- Integration with github (so we can download the lambda function from there given the link)
- Monitoring around lambda functions
- Centralized Logging (or ability to route logs) to log server
- CI/ CD for lambda functions
