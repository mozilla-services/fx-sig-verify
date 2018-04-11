# Check that we can correctly extract the cloudwatch data

from collections import namedtuple
import re

from analyze_cloudwatch import main as analyze_cloudwatch

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


LineData = namedtuple('LineData', 'value text'.split())
expected_values_by_row = [5, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, None, 0, None, 5]


def extract_data(line):
    # first item on line is a formated number (has commas)
    # extract that and convert to number
    # return a data tuple
    line = line.strip()
    try:
        possible_num = line.split(None, 1)[0]
        value = int(possible_num, 10)
    except (IndexError, ValueError):
        value = None
    return LineData(value, line)


def test_exclusion_counts(capsys):
    # Given a data file with various exclusion records
    # When we ask for exclusion counts
    analyze_cloudwatch(['--json', '--summarize', DATA_FILE])
    stdout, stderr = capsys.readouterr()
    lines = []
    for line in stdout.split('\n'):
        # convert the line into a number & line
        line_data = extract_data(line)
        lines.append(line_data)
    # Then the numbers should match what we expect:
    for i, row_value in enumerate(expected_values_by_row):
        print("{}~{}; '{}'".format(lines[i].value, row_value, lines[i].text))
        assert lines[i].value == row_value
