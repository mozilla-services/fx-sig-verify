# Check that we can correctly process consistency checks


import pytest

from analyze_cloudwatch import main as analyze_cloudwatch

passing_data_files = [
    "tests/data/cloud_watch_data.txt",
]

failing_data_files = [
    "tests/data/cw_log_s3_fail_2_runs.txt",
    "tests/data/cw_log_s3_fail_3_runs.txt",
]


@pytest.mark.parametrize('log_file', passing_data_files)
def test_valid_log(log_file, capsys):
    analyze_cloudwatch(['--consistency-check', log_file])
    stdout, stderr = capsys.readouterr()
    assert len(stdout) == 0
    assert len(stderr) == 0


@pytest.mark.parametrize('log_file', failing_data_files)
def test_inconsistent_log(log_file, capsys):
    analyze_cloudwatch(['--consistency-check', log_file])
    stdout, stderr = capsys.readouterr()
    assert "Consistency error:\n" in stdout
    assert len(stderr) == 0
