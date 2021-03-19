
import pytest
from fx_sig_verify.cli import main


def good_files():
    data_file_path = "tests/data/"
    valid_sig_list = (
        "32bit.exe",
        "32bit_new.exe",
        "32bit_sha1.exe",
        "2019-06-64bit.exe",
        "2020-05-32bit.exe",
        "FxSetup-87.0b2.exe",
    )
    return [data_file_path + x for x in valid_sig_list]


@pytest.mark.parametrize("successful_invocation", good_files())
def test_good_signature(successful_invocation):
    # GIVEN: a command line that should succeed
    cmd_line = [successful_invocation]
    # WHEN: main is called for that file
    with pytest.raises(SystemExit) as e:
        main(cmd_line)
    # THEN: it will complete successfully
    assert e.value.code == 0


def bad_files():
    data_file_path = "tests/data/"
    invalid_sig_list = (
        "PostBalrogStub.exe",
        "bad_1.exe",
        "bad_2.exe",
        "signtool.exe",
        "vswriter.exe",
    )
    return [data_file_path + x for x in invalid_sig_list]


@pytest.mark.parametrize("invalid_file", bad_files())
def test_bad_signature(invalid_file):
    # GIVEN: a command line that should fail in the arg parser
    cmd_line = [invalid_file]
    # WHEN: main is called with that file name
    with pytest.raises(SystemExit) as e:
        main(cmd_line)
    # THEN: it will fail with exit code 1
    assert e.value.code == 1
