import pytest
from analyze_cloudwatch import main


help_invocation_list = [
    "-h".split(),
    "--help".split(),
    "--help file_1 file_2".split(),  # magic args have
                                     # priority
]


@pytest.mark.parametrize('help_request', help_invocation_list)
def test_main_help(help_request):
    # GIVEN: a command line that should succeed
    # WHEN: main is called with that command line
    with pytest.raises(SystemExit) as e:
        main(help_request)
    # THEN: it will complete successfully
    assert e.value.code == 0


invalid_invocation_list = [
    "-i".split(),
    "--helx".split(),
    "file_1 file_2".split(),  # 2 files not allowed
    "-v".split(),
    "--verbose".split(),
]


@pytest.mark.parametrize('invalid_cmd_line', invalid_invocation_list)
def test_bad_command_lines(invalid_cmd_line):
    # GIVEN: a command line that should fail in the arg parser
    # WHEN: main is called with that command line
    with pytest.raises(SystemExit) as e:
        main(invalid_cmd_line)
    # THEN: it will fail with exit code 2
    assert e.value.code == 2
