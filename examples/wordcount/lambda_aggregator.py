import json
import boto3
import base64


OUTBOUND_EVENT = 'FileAggregated'


def aggregate(event, context):
    kinesis = boto3.client('kinesis')
    print("Received event: " + json.dumps(event, indent=4))
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data'])
        print("Decoded payload: " + payload)

        try:
            payload = json.loads(payload)
            execution_id = payload.get('execution_id')
            words_filtered = payload['words_filtered']

            # Filter non words
            words_aggregated = {}
            for w in words_filtered:
                if w not in words_aggregated.keys():
                    words_aggregated[w] = 1
                else:
                    count = words_aggregated[w]
                    words_aggregated[w] = count + 1

            data = json.dumps({
                'execution_id': execution_id,
                'words_aggregated': words_aggregated
            })
            kinesis.put_record(StreamName=OUTBOUND_EVENT, Data=data, PartitionKey=data)
        except Exception as ex:
            print "Error processing record, error=%s" % str(object=ex)

    return 'Processed all records.'
