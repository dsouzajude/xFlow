import json
import boto3
import base64

OUTBOUND_EVENT = 'FileDownloaded'


def read(event, context):
    kinesis = boto3.client('kinesis')
    print("Received event: " + json.dumps(event, indent=4))
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data'])
        print("Decoded payload: " + payload)

        payload = json.loads(payload)
        execution_id = payload.get('execution_id')
        data = json.dumps({
            'execution_id': execution_id,
            'contents': payload['message']
        })
        kinesis.put_record(StreamName=OUTBOUND_EVENT, Data=data, PartitionKey=data)

    return 'Processed all records.'
