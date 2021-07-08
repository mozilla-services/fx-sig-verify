# for 'fail' cases, they should be reported to SNS always

import json
import os
from moto import mock_s3, mock_sns, mock_sqs
import pytest
import tests.utils as u

from fx_sig_verify.validate_moz_signature import (lambda_handler, )  # noqa: E402


@pytest.fixture(scope='module', autouse=True)
def disable_production_filtering():
    # we want to process "invalid" files during testing
    os.environ['PRODUCTION'] = "0"


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('set_verbose_false', u.set_verbose_false_list)
@pytest.mark.parametrize('fname', u.bad_file_names_list)
def test_fail_message_when_not_verbose(set_verbose_false, fname):
    queue = u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that VERBOSE is not set
    set_verbose_false()
    # WHEN a bad file is processed
    u.upload_file(bucket, fname)
    event = u.build_event(bucket.name, fname)
    response = lambda_handler(event, u.dummy_context)
    # THEN there should be a message
    count, msg_json = u.get_one_message(queue)
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
@pytest.mark.parametrize('set_verbose_true', u.set_verbose_true_list)
@pytest.mark.parametrize('fname', u.bad_file_names_list)
def test_fail_message_when_verbose(set_verbose_true, fname):
    queue = u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that VERBOSE is set
    set_verbose_true()
    # WHEN a bad file is processed
    u.upload_file(bucket, fname)
    event = u.build_event(bucket.name, fname)
    response = lambda_handler(event, u.dummy_context)
    print("response:", response)
    # THEN there should be a message
    count, msg_json = u.get_one_message(queue)
    msg_dict = json.loads(msg_json)
    msg = msg_dict['Message']
    print("message:", msg)
    assert "fail" in response['results'][0]['status']
    assert count is 1 and msg.startswith('fail for')
