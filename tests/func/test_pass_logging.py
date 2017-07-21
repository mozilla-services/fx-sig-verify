# for 'pass' cases, they should be reported to SNS only if VERBOSE is trueish

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
def good_files():
    payload = ['32bit.exe',  # signed with older valid key
               '32bit_new.exe',  # signed with current valid key
               '32bit+new.exe',  # valid, but S3 naming issue (issue #14)
               ]
    print(payload)
    return payload


def delete_verbose():
    try:
        del os.environ['VERBOSE']
    except KeyError:
        pass


def zero_verbose():
    os.environ['VERBOSE'] = '0'


def unset_verbose():
    os.environ['VERBOSE'] = ''


@pytest.fixture
def set_verbose_false():
    return [delete_verbose, zero_verbose, unset_verbose]


def one_verbose():
    os.environ['VERBOSE'] = '1'


def two_verbose():
    # 2 is debug level
    os.environ['VERBOSE'] = '2'


def true_verbose():
    os.environ['VERBOSE'] = 'True'


@pytest.fixture
def set_verbose_true():
    return [one_verbose, two_verbose, true_verbose]


def create_bucket():
    conn = boto3.resource('s3', region_name='us-east-1')
    bucket = conn.create_bucket(Bucket=bucket_name)
    return bucket


def upload_file(bucket, filename):
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    fname = os.path.join(data_dir, filename)
    # to replicate S3 functionality, change any space in file name to a '+'
    # see issue #14
    key_name = filename.replace(' ', '+')
    bucket.put_object(Body=open(fname, 'r'), Key=key_name)
    return [(bucket_name, filename), ]


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
def test_pass_no_message_when_no_verbose(set_verbose_false, good_files):
    queue = setup_aws_mocks()
    bucket = create_bucket()
    # Given that VERBOSE is not set
    for falsey in set_verbose_false:
        falsey()
        # WHEN a good file is processed
        for fname in good_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            # THEN there should be no message
            count, msg = get_one_message(queue)

            # print things that will be useful to debug
            print("response:", response)
            print("message:", msg)
            print("count:", count)

            # actual criteria to pass
            assert "pass" in response['results'][0]['status']
            assert count is 0 and msg is ""


@mock_s3
@mock_sns
@mock_sqs
def test_pass_message_when_verbose(set_verbose_true, good_files):
    queue = setup_aws_mocks()
    bucket = create_bucket()
    # Given that VERBOSE is set
    for truthy in set_verbose_true:
        truthy()
        # WHEN a good file is processed
        for fname in good_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            print("response:", response)
            # THEN there should be no message
            count, msg = get_one_message(queue)
            print("message:", msg)
            assert "pass" in response['results'][0]['status']
            assert count is 1 and msg.startswith('pass for')
