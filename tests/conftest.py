# Fixtures needed everywhere

import pytest
import os


@pytest.fixture(scope="session", autouse=True)
def setup_environment_for_moto():
    """ Moto has some requirements """
    # Even with no connection, moto needs a valid region to find a URL
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
