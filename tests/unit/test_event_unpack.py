# Check that we can correctly unpack the 2 types of payloads given as input to
# the lambda function:
#   1. S3 events
#   2. SNS wrappers of S3 events
#
# In both cases, multiple events can be contained in the payload


import json

from fx_sig_verify.validate_moz_signature import (unpacked_s3_events, )


def build_S3_event(bucket, key, count=1):
    event_list = []
    for i in range(count):
        record = {'s3': {'bucket': {'name': "bucket{}".format(i)},
                         'object': {'key': "key{}".format(i)},
                         },
                  "eventVersion": "2.0",
                  "eventSource": "aws:s3",
                  }
        event_list.append(record)
    return {'Records': event_list, }


def build_SNS_event(s3_events):
    record = {
        "EventVersion": "1.0",
        "EventSource": "aws:sns",
        'Sns': {
            "Message": json.dumps(s3_events),
        },
    }
    return {'Records': [record, ]}


def test_s3_event():
    # Given that there is only 1 s3 event
    events = build_S3_event('bogus', 'bogus')
    # WHEN the events are separated
    s3_artifacts = list(unpacked_s3_events(events))
    # THEN there should be just one value
    assert len(s3_artifacts) == 1
    assert s3_artifacts[0] == events['Records'][0]


def test_s3_events():
    # Given that there are multiple s3 events
    elementCount = 3
    events = build_S3_event('bogus', 'bogus', elementCount)
    # WHEN the events are separated
    s3_artifacts = list(unpacked_s3_events(events))
    # THEN there should be the correct values
    assert len(s3_artifacts) == elementCount
    for orig, extracted in zip(events['Records'], s3_artifacts):
        assert orig == extracted


def test_sns_event():
    # Given that there is only 1 sns event with 1 s3 event
    s3_events = build_S3_event('bogus', 'bogus')
    events = build_SNS_event(s3_events)
    # WHEN the events are separated
    s3_artifacts = list(unpacked_s3_events(events))
    # THEN there should be just one value
    assert len(s3_artifacts) == 1
    assert s3_events['Records'][0] == s3_artifacts[0]


def test_sns_events():
    # Given that there is 1 sns event with  multiple s3 events
    elementCount = 3
    s3_events = build_S3_event('bogus', 'bogus', elementCount)
    events = build_SNS_event(s3_events)
    # WHEN the events are separated
    s3_artifacts = list(unpacked_s3_events(events))
    # THEN there should be the correct values
    assert len(s3_artifacts) == elementCount
    for orig, extracted in zip(s3_events['Records'], s3_artifacts):
        assert orig == extracted
