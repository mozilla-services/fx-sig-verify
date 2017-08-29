# for 'fail' cases, they should be reported to SNS always

import boto3
import os
import json
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
def disable_production_filtering():
    # we want to process "invalid" files during testing
    os.environ['PRODUCTION'] = "0"


@pytest.fixture(scope='module', autouse=True)
def disable_xray():
    # at the moment, 'moto' doesn't support xray, so I've hacked fleece to allow
    # an environment variable to disable them.
    os.environ['XRAY_DISABLE'] = 'True'
    # AWS Region must be valid - the API endpoint is looked up even
    # with offline testing
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    # Specify bogus credentials to avoid credential lookup
    os.environ['AWS_ACCESS_KEY_ID'] = 'bogus'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'bogus'
    os.environ['AWS_SECURITY_TOKEN'] = 'bogus'
    os.environ['AWS_SESSION_TOKEN'] = 'bogus'


def build_event(bucket, key):
    record = {'s3': {'bucket': {'name': bucket},
                     'object': {'key': key},
                     },
              }
    return {'Records': [record, ]}


@pytest.fixture()
def bad_files():
    payload = ['bad_1.exe', ]
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
    bucket.put_object(Body=open(fname, 'r'), Key=filename)
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
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    return (len(messages), messages[0].body) if len(messages) else (0, '')


@mock_s3
@mock_sns
@mock_sqs
def test_fail_message_when_not_verbose(set_verbose_false, bad_files):
    queue = setup_aws_mocks()
    bucket = create_bucket()
    # Given that VERBOSE is not set
    for falsey in set_verbose_false:
        falsey()
        # WHEN a bad file is processed
        for fname in bad_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            # THEN there should be a message
            count, msg_json = get_one_message(queue)
            msg_dict = json.loads(msg_json)
            msg = msg_dict['Message']

            # print things that will be useful to debug
            print("response:", response)
            print("message:", msg)
            print("count:", count)

            # actual criteria to pass
            assert "fail" in response['results'][0]['status']
            assert count is 1 and msg.startswith('fail for')


@mock_s3
@mock_sns
@mock_sqs
def test_fail_message_when_verbose(set_verbose_true, bad_files):
    queue = setup_aws_mocks()
    bucket = create_bucket()
    # Given that VERBOSE is set
    for truthy in set_verbose_true:
        truthy()
        # WHEN a bad file is processed
        for fname in bad_files:
            upload_file(bucket, fname)
            event = build_event(bucket.name, fname)
            response = lambda_handler(event, dummy_context)
            print("response:", response)
            # THEN there should be a message
            count, msg_json = get_one_message(queue)
            msg_dict = json.loads(msg_json)
            msg = msg_dict['Message']
            print("message:", msg)
            assert "fail" in response['results'][0]['status']
            assert count is 1 and msg.startswith('fail for')
