# Check that we can correctly extract the cloudwatch data


import re

from analyze_cloudwatch import main as analyze_cloudwatch
from functools import reduce

DATA_FILE = "tests/data/cloud_watch_data.txt"

# Cloudwatch lines start with UTC timestamp. E.g:
#   2017-10-23T00:00:13.896Z {"input_event":
JSON_PATTERN = re.compile(r'''^\S+Z {''')
REPORT_PATTERN = re.compile(r'''^\S+Z REPORT''')


def test_json_extract(capsys):
    # make sure each json record gets output on a separate line
    with open(DATA_FILE, 'r') as f:
        json_count = reduce(lambda x, y: x + y,
                            [1 for l in f if JSON_PATTERN.match(l)],
                            0)
    analyze_cloudwatch(['--json', DATA_FILE])
    stdout, _ = capsys.readouterr()
    output_lines = len(stdout.split('\n'))
    if stdout.endswith('\n'):
        # don't count the final line if empty
        output_lines -= 1
    assert output_lines == json_count


def test_report_extract(capsys):
    # make sure each non-json record gets output on a separate line
    with open(DATA_FILE, 'r') as f:
        report_count = reduce(lambda x, y: x + y,
                              [1 for l in f if REPORT_PATTERN.match(l)],
                              0)
    analyze_cloudwatch(['--report', DATA_FILE])
    stdout, stderr = capsys.readouterr()
    output_lines = len(stdout.split('\n'))
    if stdout.endswith('\n'):
        # don't count the final line if empty
        output_lines -= 1
    assert output_lines == report_count
