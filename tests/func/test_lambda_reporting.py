# For any case, logs should be sent to CloudWatch (aka, stdout)

from moto import mock_s3, mock_sns, mock_sqs
import pytest
import tests.utils as u

from fx_sig_verify.validate_moz_signature import (lambda_handler, )  # noqa: E402


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('fname', u.bad_file_names_list +
                                  u.good_file_names_list)
@pytest.mark.parametrize('setter', u.set_verbose_true_list[:1] +
                                   u.set_production_false_list[:1])
def test_always_log_output_issue_17(setter, fname, capsys):
    # mock the queue, but we won't examine it
    u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that VERBOSE is in any state
    setter()
    # WHEN any file is processed
    bucket_name, key_name = u.upload_file(bucket, fname)
    event = u.build_event(bucket_name, key_name)
    results = lambda_handler(event, u.dummy_context)
    # THEN there should always be a message on stdout
    out, err = capsys.readouterr()
    # put useful information in failure output
    print("response: '{}'".format(results))
    print(f"stdout:\n{out}\n\nstderr:\n{err}")
    assert out != ''
    assert err == ''


@mock_s3
@mock_sns
@mock_sqs
def test_raise_exception_on_S3_error():
    # GIVEN we're running in lambda
    # mock the queue, but we won't examine it
    u.setup_aws_mocks()
    u.create_bucket()
    # WHEN a non existant file is processed
    # (S3 only guarantees eventual consistancy)
    bucket_name, key_name = 'bogus_bucket', 'firefox-bogus.exe'
    event = u.build_event(bucket_name, key_name)
    # THEN we raise an error (so AWS will retry)
    with pytest.raises(IOError):
        results = lambda_handler(event, u.dummy_context)
    # and function should not have returned
    assert 'results' not in list(locals().keys())
