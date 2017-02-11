import json
import boto3
import base64


OUTBOUND_EVENT = 'FileFiltered'
LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def reword(word):
    ''' Removes non-letters from word '''
    reworded = ''
    for letter in word:
        if letter not in LETTERS:
            continue
        reworded = reworded + letter
    return reworded


def is_word(word):
    if len(word) <= 1:
        return False
    return True


def filter_out_non_words(event, context):
    kinesis = boto3.client('kinesis')
    print("Received event: " + json.dumps(event, indent=4))
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data'])
        print("Decoded payload: " + payload)

        try:
            payload = json.loads(payload)
            execution_id = payload.get('execution_id')
            words_arr = payload['words_arr']

            # Filter non words
            words_filtered = []
            for w in words_arr:
                reworded = reword(w)
                if not reworded:
                    continue
                if not is_word(reworded):
                    continue
                words_filtered.append(reworded)

            data = json.dumps({
                'execution_id': execution_id,
                'words_filtered': words_filtered
            })
            kinesis.put_record(StreamName=OUTBOUND_EVENT, Data=data, PartitionKey=data)
        except Exception as ex:
            print "Error processing record, error=%s" % str(object=ex)

    return 'Processed all records.'
