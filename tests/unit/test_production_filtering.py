# In production, we filter out "don't care" exe's and non-exe's
# The decisions are made on the last elemement of the key name, and the desired
# truth table is as follows:
#
#   +-------------+-------+----------+
#   | Production? | Good? | Exclude? |
#   +-------------+-------+----------+
#   |     Y       |   Y   |    N     |
#   +-------------+-------+----------+
#   |     Y       |   n   |    Y     |
#   +-------------+-------+----------+
#   |     n       |   Y   |    N     |
#   +-------------+-------+----------+
#   |     n       |   n   |    N     |
#   +-------------+-------+----------+


from moto import mock_s3, mock_sns, mock_sqs
import pytest
import tests.utils as u

from fx_sig_verify.validate_moz_signature import (lambda_handler, )  # noqa: E402


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('fname', u.good_file_names_list +
                                  u.bad_file_names_list)
@pytest.mark.parametrize('set_production_false',
                         u.set_production_false_list[:1])
def test_no_exclude_message_when_not_production(set_production_false,
                                                fname):
    u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that PRODUCTION is set to False
    set_production_false()
    # WHEN any file is processed
    u.upload_file(bucket, fname)
    event = u.build_event(bucket.name, fname)
    response = lambda_handler(event, u.dummy_context)
    # THEN there should be no mentions of skipping
    # count, msg = get_one_message(queue)

    # print things that will be useful to debug
    print("response:", response)

    # actual criteria to pass
    assert u.not_in("Excluded from validation",
                    response['results'][0]['results'])


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('key', u.bad_key_names_list)
@pytest.mark.parametrize('fname', u.bad_file_names_list)
@pytest.mark.parametrize('set_production_true', u.set_prod_true_list[:1])
def test_exclude_message_when_production(set_production_true, fname,
                                         key):
    u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that PRODUCTION is missing or true
    set_production_true()
    # WHEN a bad file is processed:
    u.upload_file(bucket, fname, key)
    event = u.build_event(bucket.name, key)
    response = lambda_handler(event, u.dummy_context)
    print("response:", response)
    # THEN it should pass & be marked as excluded
    assert "pass" in response['results'][0]['status']
    assert u.is_in("Excluded from validation", response['results'],
                   'results')


@mock_s3
@mock_sns
@mock_sqs
@pytest.mark.parametrize('key', u.good_key_names_list)
@pytest.mark.parametrize('fname', u.good_file_names_list)
@pytest.mark.parametrize('set_production_true', u.set_prod_true_list[:1])
def test_no_exclude_production(set_production_true, fname, key):
    u.setup_aws_mocks()
    bucket = u.create_bucket()
    # Given that PRODUCTION is missing or true
    set_production_true()
    # WHEN a good file is processed, using any valid key
    u.upload_file(bucket, fname, key)
    event = u.build_event(bucket.name, key)
    response = lambda_handler(event, u.dummy_context)
    #  print("response:", response)
    # THEN it should pass & not be marked as excluded
    assert "pass" in response['results'][0]['status']
    assert u.not_in("Excluded from validation",
                    response['results'][0]['results'])
