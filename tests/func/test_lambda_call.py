import os
import json
import pytest
from fx_sig_verify.validate_moz_signature import lambda_handler


@pytest.fixture(scope='module', autouse=True)
def setup_environment():
    os.environ['SNSARN'] = 'arn:aws:sns:us-west-2:927034868273:hwine-exe-bad'


@pytest.fixture()
def load_all_tasks():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    fname = os.path.join(data_dir, "S3_event_template.json")
    event = json.loads(open(fname, 'r').read())
    return event


def test_lambda_call(load_all_tasks):
    # this should exercise almost all code paths, and therefore find all the
    # syntax errors! There would be a huge number of real errors, of course.
    assert callable(lambda_handler)
    lambda_handler(load_all_tasks, None)
