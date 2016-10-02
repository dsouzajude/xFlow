
xFlow
=====
A serverless workflow architecture using AWS Lambda functions.

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

workflow_id: word_count
description: A flow that takes as input a file and counts the unique words in it.
steps:
- name: lambda_file_reader
  description: Downloads the file and publishes `FileDownloaded` event with the contents in it.
  source: s3://flows/word_count/reader.py
  handler: read_file
  events:
    - FileUploaded
- name: lambda_parser
  description: Reads contents, parses it into an array of words and publishes a `FileParsed` event with the data in it.
  source: s3://flows/word_count/parser.py
  handler: parse
  events:
    - FileDownloaded
- name: lambda_combiner
  description: Groups similar words and aggregates the count and publishes a `FileAggregated` with the grouping in it.
  source: s3://flows/word_count/combiner.py
  handler: parse
  events:
    - FileParsed
- name: lambda_filter
  description: Filters out non-words and publishes a 'FileFiltered' with the remainder words in it.
  source: s3://flows/word_count/filter.py
  handler: filter
  events: [FileAggregated]
- name: lambda_summarize
  description: Outputs the word count for every unique word and total words in the file.
  source: git://project/blob/master/flows/word_count/summary.py
  handler: summarize
  events:
    - FileFiltered

```

- Setup the workflow via the following command:

  `xflow setup -file word_count.cfg`

  Behind the scenes, this will do the following:
  - Create (or update) AWS Lambda functions.
  - For each lambda function, subscribe them to AWS Kinesis based on the events they are listening for.
  - Lambda functions will be executed once an event is published to AWS Kinesis.

- Tracking the workflow is done via the following command:

  `xflow track -flow word_count -execution_id 112233`


xFlow Requirements (and roadmap):
=================================
- Integration with github (so we can download the lambda function from there given the link)
- Lambda functions can subscribe to events
- Lambda functions can publish events
- Monitoring around lambda functions
- Centralized Logging (or ability to route logs) to log server
- Tracking execution in a workflow (via unique `execution_id` which is common to all steps in the workflow)
- CI/ CD for lambda functions
