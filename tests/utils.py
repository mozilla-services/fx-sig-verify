# utilities that I couldn't get in fixtures yet

import os
from moto import mock_s3, mock_sns, mock_sqs

__all__ = ['dummy_context', 'build_event', 'upload_file', ]

class DummyContext(object):
    aws_request_id = 'DUMMY ID'
dummy_context = DummyContext()


def build_event(bucket, key):
    record = {'s3': {'bucket': {'name': bucket},
                     'object': {'key': key},
                     },
              }
    return {'Records': [record, ]}


@mock_s3
def upload_file(bucket, filename):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    fname = os.path.join(data_dir, filename)
    s3_object = bucket.put_object(Body=open(fname, 'r'), Key=filename)
    return [(s3_object.bucket_name, s3_object.key), ]
