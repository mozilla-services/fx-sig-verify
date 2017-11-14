# Check that we are munging the subject correctly for SNS messages


import boto3
import json
import os
from moto import mock_sns, mock_sqs
import pytest
from fx_sig_verify.validate_moz_signature import (MozSignedObjectViaLambda, )

# constants used by fixtures and test code
sqs_name = "test-queue"
PREFIX = "pass for s3://"
SUFFIX = "last_part_of_file.txt"
REPLACEMENT_SUBJECT = "Truncated subject, examine message"


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


@pytest.fixture()
def good_line():
    payload = [
        "50 " + 'x'*47,
        "99 " + 'x'*96,
    ]
    return payload


@pytest.fixture()
def long_fixable_lines():
    payload = [
        PREFIX + "x/"*50 + SUFFIX,
        PREFIX + "/"*150 + SUFFIX,
        PREFIX + "x"*150 + '/' + SUFFIX,
        # real message
        "fail for s3://net-mozaws-prod-delivery-firefox/pub/firefox/releases/"
        "52.5.0esr/win32-sha1/ms/Firefox Setup 52.5.0esr.exe",
    ]
    return payload


@pytest.fixture()
def unfixable_lines():
    payload = [
        "too long" * 20,  # no '/' for split
        "x"*110 + PREFIX + SUFFIX,  # splitable, but still too long
    ]
    return payload


@mock_sns
@mock_sqs
def test_good(good_line):
    queue = setup_aws_mocks()
    out = MozSignedObjectViaLambda('bucket', 'key')
    for line in good_line:
        out.send_sns(line)
        count, msg_json = get_one_message(queue)
        assert count == 1
        # Subject shouldn't be changed
        msg = json.loads(msg_json)
        assert line == msg['Subject']

    # TODO retrieve message from sqs & verify length after moto fix to pass
    # subject through (atm, passes fixed value of 'my subject')


@mock_sns
@mock_sqs
def test_fixable(long_fixable_lines):
    queue = setup_aws_mocks()
    out = MozSignedObjectViaLambda('bucket', 'key')
    for l in long_fixable_lines:
        out.send_sns(l)
        count, msg_json = get_one_message(queue)
        assert count == 1
        msg = json.loads(msg_json)
        subject = msg['Subject']
        print("subject  in: ", l)
        print("subject out: ", subject)
        assert " for s3: " in subject
        assert len(subject) < 100


@mock_sns
@mock_sqs
def test_unfixable(unfixable_lines):
    queue = setup_aws_mocks()
    out = MozSignedObjectViaLambda('bucket', 'key')
    for l in unfixable_lines:
        out.send_sns(l)
        count, msg_json = get_one_message(queue)
        assert count == 1
        msg = json.loads(msg_json)
        subject = msg['Subject']
        print("subject in: ", l)
        assert REPLACEMENT_SUBJECT == subject
