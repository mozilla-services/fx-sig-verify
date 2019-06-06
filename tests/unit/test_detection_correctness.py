
import pytest
from fx_sig_verify.cli import main


@pytest.fixture()
def successful_invocations():
    data_file_path = "tests/data/"
    valid_sig_list = (
        "32bit.exe",
        "32bit_new.exe",
        "32bit_sha1.exe",
        "2019-06-64bit.exe",
    )
    return map(lambda x: [data_file_path + x], valid_sig_list)


def test_good_signature(successful_invocations):
    # GIVEN: a command line that should succeed
    for cmd_line in successful_invocations:
        # WHEN: main is called with that command line
        with pytest.raises(SystemExit) as e:
            main(cmd_line)
        # THEN: it will complete successfully
        assert e.value.code == 0


@pytest.fixture()
def invalid_invocations():
    data_file_path = "tests/data/"
    invalid_sig_list = (
        "PostBalrogStub.exe",
        "bad_1.exe",
        "bad_2.exe",
        "signtool.exe",
        "vswriter.exe",
    )
    return map(lambda x: [data_file_path + x], invalid_sig_list)


def test_bad_signature(invalid_invocations):
    # GIVEN: a command line that should fail in the arg parser
    for cmd_line in invalid_invocations:
        # WHEN: main is called with that command line
        with pytest.raises(SystemExit) as e:
            main(cmd_line)
        # THEN: it will fail with exit code 1
        assert e.value.code == 1
