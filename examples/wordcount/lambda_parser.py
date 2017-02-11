import base64
import boto3
import json

OUTBOUND_EVENT = 'FileParsed'


def parse(event, context):
    kinesis = boto3.client('kinesis')
    print("Received event: " + json.dumps(event, indent=4))
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data'])
        print("Decoded payload: " + payload)

        payload = json.loads(payload)

        try:
            execution_id = payload.get('execution_id')
            contents = payload['contents']
            words_arr = contents.split()
            data = json.dumps({
                'execution_id': execution_id,
                'words_arr': words_arr
            })
            kinesis.put_record(StreamName=OUTBOUND_EVENT, Data=data, PartitionKey=data)
            print("Published: %s" % data)
        except Exception as ex:
            print "Error processing record, error=%s" % str(object=ex)

        return 'Successfully processed record.'
