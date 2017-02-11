import json
import boto3
import base64

OUTBOUND_EVENT = 'FileSummarized'


def summarize(event, context):
    kinesis = boto3.client('kinesis')
    print("Received event: " + json.dumps(event, indent=4))
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data'])
        print("Decoded payload: " + payload)

        try:
            payload = json.loads(payload)
            execution_id = payload.get('execution_id')
            words_aggregated = payload['words_aggregated']

            # Group and count similar words
            summary = {
                'total': len(words_aggregated.keys()),
                'counts': {}
            }
            for word, count in words_aggregated.iteritems():
                summary['counts'][word] = count
            data = json.dumps({
                'execution_id': execution_id,
                'summary': summary
            })
            print 'Summary'
            print json.dumps(summary, indent=4)
            kinesis.put_record(StreamName=OUTBOUND_EVENT, Data=data, PartitionKey=data)
        except Exception as ex:
            print "Error processing record, error=%s" % str(object=ex)

    return 'Processed all records.'
