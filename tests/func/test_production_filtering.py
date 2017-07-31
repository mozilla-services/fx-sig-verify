# In production, we filter out "don't care" exe's

import boto3
import os
from moto import mock_s3, mock_sns, mock_sqs
import pytest

from fx_sig_verify.validate_moz_signature import (lambda_handler, )  # noqa: E402

# Constants
bucket_name = 'pseudo-bucket'
sqs_name = "test-queue"


class DummyContext(object):
    aws_request_id = 'DUMMY ID'


dummy_context = DummyContext()


def not_in(text, array, array2=None):
    # return true if text is not in any element of the array
    result = True
    for line in array:
        if array2:
            for l2 in line[array2]:
                if text in l2:
                    result = False
                    break
        elif text in line:
            result = False
        if not result:
            break
    return result


def is_in(text, array, array2=None):
    return not not_in(text, array, array2)


@pytest.fixture(scope='module', autouse=True)
def disable_production_filtering():
    # we want to process "invalid" files during testing
    os.environ['PRODUCTION'] = "0"


@pytest.fixture(scope='module', autouse=True)
def disable_xray():
    # at the moment, 'moto' doesn't support xray, so I've hacked fleece to allow
    # an environment variable to disable them.
    os.environ['XRAY_DISABLE'] = 'True'


def build_event(bucket, key):
    record = {'s3': {'bucket': {'name': bucket},
                     'object': {'key': key},
                     },
              }
    return {'Records': [record, ]}


@pytest.fixture()
def good_keys():
    payload = [
        "Firefox",
        "Firefox sadf asfsd.exe",
        "firefox",
        "firefox-asdjsll.exe",
        "/nightly/fred/firefox-asdkjds.exe",
        "/release/sam/Firefox asdfe sss.exe",
    ]
    return payload


@pytest.fixture()
def bad_files():
    payload = ['bad_1.exe', ]
    print(payload)
    return payload


@pytest.fixture()
def good_files():
    payload = ['32bit.exe',  # signed with older valid key
               '32bit_new.exe',  # signed with current valid key
               '32bit+new.exe',  # valid, but S3 naming issue (issue #14)
               ]
    print(payload)
    return payload


def delete_production():
    try:
        del os.environ['PRODUCTION']
    except KeyError:
        pass


def zero_production():
    os.environ['PRODUCTION'] = '0'


def unset_production():
    os.environ['PRODUCTION'] = ''


@pytest.fixture
def set_production_false():
    return [zero_production, ]


def true_production():
    os.environ['PRODUCTION'] = '1'


@pytest.fixture
def set_production_true():
    return [delete_production, true_production, unset_production]


def create_bucket():
    conn = boto3.resource('s3', region_name='us-east-1')
    bucket = conn.create_bucket(Bucket=bucket_name)
    return bucket


def upload_file(bucket, filename, key_name=None):
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    fname = os.path.join(data_dir, filename)
    # to replicate S3 functionality, change any space in file name to a '+'
    # see issue #14
    if not key_name:
        # if a keyname isn't specified, build one
        key_name = filename.replace(' ', '+')
    bucket.put_object(Body=open(fname, 'r'), Key=key_name)
    return [(bucket_name, key_name), ]


def setup_aws_mocks():
    # mock the SNS topic & pass via environment
    client = boto3.client("sns")
    client.create_topic(Name="some-topic")
    response = client.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']
    os.environ['SNSARN'] = topic_arn

    # setup an sqs queue to pull the message from
    sqs_conn = boto3.resource('sqs', region_name='us-east-1')
    sqs_conn.create_queue(QueueName=sqs_name)

    client.subscribe(TopicArn=topic_arn,
                     Protocol="sqs",
                     Endpoint="arn:aws:sqs:us-east-1:123456789012:test-queue")
    queue = sqs_conn.get_queue_by_name(QueueName=sqs_name)
    return queue


def get_one_message(queue):
    # get more than one to detect double push
    messages = queue.receive_messages(MaxNumberOfMessages=10)
    return (len(messages), messages[0].body) if len(messages) else (0, '')


@mock_s3
@mock_sns
@mock_sqs
def test_no_exclude_message_when_not_production(set_production_false,
                                                good_files, bad_files):
    setup_aws_mocks()
    bucket = create_bucket()
    # Given that PRODUCTION is set to False
    for falsey in set_production_false:
        falsey()
        # WHEN any file is processed
        for fname in good_files + bad_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            # THEN there should be no mentions of skipping
            # count, msg = get_one_message(queue)

            # print things that will be useful to debug
            print("response:", response)

            # actual criteria to pass
            assert not_in("Excluded from validation", response['results'],
                          'results')


@mock_s3
@mock_sns
@mock_sqs
def test_exclude_message_when_production(set_production_true, good_files,
                                         bad_files):
    setup_aws_mocks()
    bucket = create_bucket()
    # Given that PRODUCTION is missing or true
    for truthy in set_production_true:
        truthy()
        # WHEN a any file is processed (since we have no "good files" that pass
        # the filter)
        for fname in good_files + bad_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            print("response:", response)
            # THEN it should pass & be marked as excluded
            assert "pass" in response['results'][0]['status']
            assert is_in("Excluded from validation", response['results'],
                         'results')


@mock_s3
@mock_sns
@mock_sqs
def test_no_exclude_production(set_production_true, good_files, good_keys):
    setup_aws_mocks()
    bucket = create_bucket()
    # Given that PRODUCTION is missing or true
    for truthy in set_production_true:
        truthy()
        # WHEN a good file is processed, using any valid key
        fname = good_files[0]
        for keyname in good_keys:
            upload_file(bucket, fname, keyname)
            event = build_event(bucket.name, keyname)
            response = lambda_handler(event, dummy_context)
            print("response:", response)
            # THEN it should pass & not be marked as excluded
            assert "pass" in response['results'][0]['status']
            assert not_in("Excluded from validation", response['results'],
                          'results')
