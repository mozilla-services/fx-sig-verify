
import pytest
from fx_sig_verify.cli import main


@pytest.fixture()
def successful_invocations():
    return ("-h".split(),
            "--help".split(),
            "--version".split(),
            "--version --help".split(),
            "--help --version".split(),  # order matters
            "--help --version file_1 file_2".split(),  # magic args have
                                                       # priority
            )


def test_main_help(successful_invocations):
    # GIVEN: a command line that should succeed
    for cmd_line in successful_invocations:
        # WHEN: main is called with that command line
        with pytest.raises(SystemExit) as e:
            main(cmd_line)
        # THEN: it will complete successfully
        assert e.value.code == 0


@pytest.fixture()
def invalid_invocations():
    return ("-i".split(),
            "--helx".split(),
            "-v".split(),
            "file_1 file_2".split(),  # 2 files not allowed
            "".split(),  # 0 files not allowed (without switches)
            )


def test_bad_command_lines(invalid_invocations):
    # GIVEN: a command line that should fail in the arg parser
    for cmd_line in invalid_invocations:
        # WHEN: main is called with that command line
        with pytest.raises(SystemExit) as e:
            main(cmd_line)
        # THEN: it will fail with exit code 2
        assert e.value.code == 2
