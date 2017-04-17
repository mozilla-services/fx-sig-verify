from __future__ import print_function
import boto3

s3_client = boto3.client('s3')


def handler(event, context):
    for record in event['Records']:

        print('Processing {0[s3][bucket][name]}/{0[s3][object][key]}'
              .format(record))
        # print('Processing {s3.bucket.name}/{s3.object.key}'.format(record))
