# for 'pass' cases, they should be reported to SNS only if VERBOSE is trueish

import json
from moto import mock_s3, mock_sns, mock_sqs
import pytest
import tests.utils as u

from fx_sig_verify.validate_moz_signature import (lambda_handler, )  # noqa: E402


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('fname', u.good_file_names_list)
@pytest.mark.parametrize('setter', u.set_verbose_false_list)
def test_pass_no_message_when_no_verbose(setter, fname):
    queue = u.setup_aws_mocks()
    bucket = u.create_bucket()
    # given that verbose is not set
    setter()
    # when a good file is processed
    bucket_name, key_name = u.upload_file(bucket, fname)
    event = u.build_event(bucket_name, key_name)
    response = lambda_handler(event, u.dummy_context)
    # THEN there should be no message
    count, msg_json = u.get_one_message(queue)
    try:
        msg_dict = json.loads(msg_json)
        msg = msg_dict['Message']
    except ValueError:
        msg = ""

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
@pytest.mark.parametrize('fname', u.good_file_names_list)
@pytest.mark.parametrize('setter', u.set_verbose_true_list)
def test_pass_message_when_verbose(setter, fname):
    queue = u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that VERBOSE is set
    setter()
    # WHEN a good file is processed
    bucket_name, key_name = u.upload_file(bucket, fname)
    event = u.build_event(bucket_name, key_name)
    response = lambda_handler(event, u.dummy_context)
    print("response:", response)
    # THEN there should be no message
    count, msg_json = u.get_one_message(queue)
    msg_dict = json.loads(msg_json)
    msg = msg_dict['Message']
    print("message:", msg)
    assert "pass" in response['results'][0]['status']
    assert count is 1 and msg.startswith('pass for')
