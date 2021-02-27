#!/usr/bin/env python


import collections
import fileinput
import json
import logging
import math
import argparse
import re
from functools import reduce

# below should probably be a parameter to the app
CONFIGURED_MAX_RUN_TIME_MS = 60 * 1000

# Below globals are needed by factory or other globals
JSON_STARTER = '{'
REPORT_STARTER = 'REPORT'
ANY_STARTER = ''

# timestamp is optional (wasn't in original logs)
# and may or may not have ANSI colorizing
# Note that only 1 trailing space is part of the timestamp
TIME_STAMP = r'''^(?:\x1b\[33m)? # ANSI coloring
                (?P<timestamp>[\d:.T-]{23}Z)?  # timestamp
                (?:\x1b\[0m)? # ANSI coloring
                \s? # trailing space
                '''

PERF_OUTPUT = """
{invocations:19,d} runs
{total_time_seconds:19,.0f} seconds execution time
{bill_time_seconds:19,.0f} seconds billed
{gb_seconds:19,.0f} GBi seconds (AWS Billing Unit)
{average_time:19,.0f} average milliseconds per run
{max_memory_invocations:19,d} times we used all memory
    {max_memory_pcnt:19.0f}% of runs maxing out memory
    {max_used_memory:19.0f} MBi max memory used
{max_time_invocations:19,d} times run aborted for excessive time
    {max_time_pcnt:19.0f}% of runs exceeding time limit
    {retry_never_succeeded:19,d} times retry did not succeed
""".strip()

JSON_OUTPUT = """
{pass:8,d} passed
        {Excluded:10,d} exe's not validated
{SigVerifyNoSignature:10,d} exe without signature
{SigVerifyBadSignature:10,d} exe with bad signature
{SigVerifyNonMozSignature:10,d} exe with non-Mozilla signature
        {S3RetrievalFailure:10,d} that couldn't be retrieved from S3
        {S3UnquoteRetry:10,d} that were retried after unquoting
        {S3UnquoteSuccess:10,d} that then succeeded
{other:10,d} other failures
       ---
{fail:8,d} total failed
--------
{total:8,d} processed
========
""".strip()
#  need the keys, as when rendered, no default values
JSON_OUTPUT_KEYS = (
    "pass",
    "Excluded",
    "SigVerifyNoSignature",
    "SigVerifyBadSignature",
    "SigVerifyNonMozSignature",
    "S3RetrievalFailure",
    "S3UnquoteRetry",
    "S3UnquoteSuccess",
    "other",
    "fail",
    "total",
)

logger = logging.getLogger(__name__)


class Summerizer(object):
    """
    Default Summerizer

    Just prints each line
    """
    def add_line(self, line):
        print(line.strip())

    def print_final_report(self):
        pass


class JsonSummerizer(Summerizer):
    """
    extract JSON data
    """

    json_pattern = re.compile(TIME_STAMP +
                              r'''\s*(?P<json>.*\S)\s*$''',
                              re.VERBOSE)

    def __init__(self, summarize=False, verbose=False, req_ids=None, **_):
        self.data = []
        self.summarize = summarize
        self.verbose = verbose

    def add_line(self, line):
        # always remove timestamp (if present)
        match = self.json_pattern.match(line)
        json_text = match.group('json')
        if self.summarize:
            datum = json.loads(json_text)
            self.data.append(datum)
        else:
            print(json_text)

    def print_final_report(self):
        if self.summarize:
            self.compute_totals()
            # HACK - since we expand counts, we need default values
            for k in JSON_OUTPUT_KEYS:
                self.counts[k] += 0
            print(JSON_OUTPUT.format(**self.counts))
        else:
            for r in self.req_ids:
                print('Log entries for request id {}\n   {}'.
                      format(r, '\n   '.join([x[:80] for x
                                              in self.details[r]])))

    def compute_totals(self):
        # ensure all keys will have some value
        def incr(d, truthy, true_key, false_key=None):
            # ensure any keys exist, so format() can grab them
            d[true_key] += 0
            if false_key:
                d[false_key] += 0
            if truthy:
                d[true_key] += 1
            elif false_key:
                d[false_key] += 1

        def endswith(list_, text):
            return reduce(lambda x, y: x or y, [z.endswith(text) for z in
                                                list_], False)

        def isin(list_, text):
            return reduce(lambda x, y: x or y, [text in z for z in list_],
                          False)

        counts = collections.Counter()
        counts['total'] = 0
        for record in self.data:
            counts['total'] += len(record['results'])
            for check in record['results']:
                incr(counts, check['status'] == "pass", "pass", "fail")
                try:
                    reasons = check['results']
                    incr(counts,
                         endswith(reasons, 'SigVerifyNoSignature'),
                         "SigVerifyNoSignature")
                    incr(counts,
                         endswith(reasons, 'SigVerifyNonMozSignature'),
                         "SigVerifyNonMozSignature")
                    incr(counts,
                         endswith(reasons, 'SigVerifyBadSignature'),
                         "SigVerifyBadSignature")
                    incr(counts,
                         isin(reasons, 'failed to process s3 object'),
                         "S3RetrievalFailure")
                    incr(counts,
                         isin(reasons, 'First get failed'),
                         "S3UnquoteRetry")
                    incr(counts,
                         isin(reasons, 'get_object worked'),
                         "S3UnquoteSuccess")
                    incr(counts,
                         isin(reasons, 'Excluded from validation by prefix'),
                         "Excluded")
                except IndexError:
                    pass
        # compute uncategorized failures
        known_fails = reduce(lambda x, y: x+y,
                             [v for k, v in counts.items()
                              if k.endswith("Signature")], 0)
        counts['other'] = counts['fail'] - known_fails
        self.counts = counts


class MetricSummerizer(Summerizer):
    """
    Accumulate Metrics from the 'REPORT' text line
    """

    report_pattern = re.compile(TIME_STAMP +
                                r'''  # noqa
                                \s*REPORT\s+
                                RequestId:\s+(?P<request_id>\S+)\s+  # a2f5e4c9-76ed-11e7-90a2-d7d797025d0c
                                Duration:\s+(?P<real_time>\S+)\s+ms\s+
                                Billed\sDuration:\s+(?P<bill_time>\d+)\s+ms\s+
                                Memory\sSize:\s+(?P<mem_allocated>\d+)\s+MB\s+
                                Max\sMemory\sUsed:\s+(?P<mem_used>\d+)\s+MB
                                \s*''', re.VERBOSE)

    def __init__(self, summarize=False, verbose=False, **_):
        self.summarize = summarize
        self.verbose = verbose
        self.retried_requests = collections.defaultdict(int)
        self.counts = {
            "invocations": 0,
            "total_time": 0,
            "bill_time": 0,
            "average_time": 0,
            "max_used_memory": 0,
            "max_memory_invocations": 0,
            "max_memory_pcnt": 0,
            "total_memory": 0,
            "total_allocated_memory": 0,
            "avg_memory": 0,
            "max_time_invocations": 0,
            "max_time_pcnt": 0,
        }

    def add_line(self, line):
        if not self.summarize:
            print(line.strip())
            return
        match = self.report_pattern.match(line.strip())
        if not match:
            raise SyntaxError("Unexpected format: '{}'".format(line.strip()))
        self.counts["invocations"] += 1
        self.counts["total_time"] += float(match.group('real_time'))
        self.counts["bill_time"] += float(match.group('bill_time'))
        self.counts["max_used_memory"] = max(float(match.group('mem_used')),
                                             self.counts["max_used_memory"])
        self.counts["total_memory"] += float(match.group('mem_used'))
        self.counts["total_allocated_memory"] = \
            float(match.group('mem_allocated'))
        if match.group('mem_allocated') == match.group('mem_used'):
            self.counts["max_memory_invocations"] += 1
        rq_id = match.group('request_id')
        if float(match.group('real_time')) >= CONFIGURED_MAX_RUN_TIME_MS:
            self.counts["max_time_invocations"] += 1
            if self.retried_requests[rq_id] < 0:
                logger.warn("{} previously successful".format(rq_id))
            else:
                self.retried_requests[rq_id] += 1
            logger.warn("{} time exceeded for request ('{}')"
                        .format(rq_id, match.group('real_time')))
        else:
            # the run succeeded, but we don't know if it's related to
            # failure(s) not (the failure message could come later in
            # the log than the success message).
            # So only boast if we know we're good
            if self.retried_requests[rq_id] > 0:
                logger.warn("{} retry successful for request (failed {} times)"
                            .format(rq_id, self.retried_requests[rq_id]))
            # but always keep track of successes to offset one failure.
            # (we haven't seen a double failure yet)
            self.retried_requests[rq_id] -= 1

    def print_final_report(self):
        self.compute_totals()
        print(PERF_OUTPUT.format(**self.counts))
        if self.verbose:
            print("Unmatched Request ID's:\n   {}".
                  format('\n   '.join(self.counts["unprocessed"])))

    def compute_totals(self):
        c = self.counts
        invocations = c["invocations"] or float('INF')
        c["average_time"] = c["total_time"] / invocations
        c["max_time_pcnt"] = c["max_time_invocations"] * 100 / invocations
        c["max_memory_pcnt"] = (c["max_memory_invocations"] * 100
                                / invocations)
        c["avg_memory"] = int(math.ceil(c["total_memory"] / invocations))
        unprocessed = [k for k, v in self.retried_requests.items()
                       if v > 0]
        c["unprocessed"] = unprocessed
        c["retry_never_succeeded"] = len(unprocessed)
        c["total_time_seconds"] = c["total_time"] / 1000
        c["bill_time_seconds"] = c["bill_time"] / 1000
        c["gb_seconds"] = (c["bill_time_seconds"] * c["total_allocated_memory"]
                           / 1024.)
        self.counts = c


class ExtractSummarizer(Summerizer):
    """
    Display all records for the specified request ids in the log file order.
    """

    # adhoc pattern
    TRACEBACK = 'Traceback'

    # compile (once) the patterns we need
    json_pattern = re.compile(TIME_STAMP + r'''
                              \s*(?P<json_string>{.*})''',
                              re.VERBOSE)
    req_id_pattern = re.compile(TIME_STAMP + r'''  # noqa
                                \s*(?P<line_type>\S+)\s+  # START, END, or REPORT
                                RequestId:\s+(?P<request_id>\S+).*''',
                                re.VERBOSE)
    traceback_pattern = re.compile(TIME_STAMP + TRACEBACK, re.VERBOSE)

    def __init__(self, req_ids=None, verbose=False, **_):
        self.details = collections.defaultdict(list)
        self.req_ids = req_ids or []
        self.consistancy_check = not bool(self.req_ids)
        self.verbose = verbose
        self.import_errors_found = False
        self.traceback_found_count = 0
        self.first_report_line_type = None
        self.last_report_line_type = None

    def parse(self, line):
        """
        Extract the request id from the given line. The line is either
        json or a report line
        """
        try:
            match = self.json_pattern.search(line)
            datum = json.loads(match.group('json_string'))
            req_id = datum['request_id']
        except (ValueError, AttributeError):
            datum = line.strip()
            match = self.req_id_pattern.search(datum)
            if match:
                req_id = match.group('request_id')
                if not self.first_report_line_type:
                    self.first_report_line_type = match.group('line_type')
                self.last_report_line_type = match.group('line_type')
            else:
                # ignore some debug lines, but do ad hoc peeks for oddities
                if "RuntimeWarning" in datum:
                    self.import_errors_found = True
                elif datum.startswith("Traceback"):
                    self.traceback_found_count += 1
                req_id = None
        return req_id, datum

    def add_line(self, line):
        req_id, datum = self.parse(line)
        if (self.consistancy_check or req_id in self.req_ids) \
                and req_id is not None:
            # we don't want to accidentally convert the json to a python dict
            self.details[req_id].append(str(datum))

    def print_consistency_errors(self):
        # each request id should have a START, END, and REPORT line, plus one
        # JSON line.
        starters = ('S', 'E', 'R', '{', )
        line_start_patterns = [re.compile(x, re.VERBOSE) for x in [TIME_STAMP+'\s*'+x for x in starters]]
        funky_count = 0
        for rqst_id, lines in self.details.items():
            counts = [0, 0, 0, 0]
            for i, pattern in enumerate(line_start_patterns):
                counts[i] = reduce(lambda x, y: x+1 if y else x,
                                   [l for l in lines if
                                    pattern.match(l)], 0)
            funky = len(lines) != 4 or counts != [1, 1, 1, 1]
            if funky:
                funky_count += 1
                print()
                if self.verbose:
                    print(counts, len(lines))
                print("Consistency error:")
                self.print_rqst(rqst_id)
        if self.verbose:
            print()
            print("Checked {} requests for consistency, found {} "
                  "inconsistencies.".
                  format(len(self.details), funky_count))
        if funky_count:
            print()  # blank line for separation

    def print_rqst(self, rqst_id, indent=None, header=True, num_cols=80):
        if indent is None:
            # allow empty string for indent
            indent = '   '
        indent = '\n' + indent
        if header:
            print("{} had {} log lines.".format(rqst_id,
                                                len(self.details[rqst_id])))
        print(indent[1:] + indent.join([str(x)[:num_cols] for x in
                                       self.details[rqst_id]]))

    def print_final_report(self):
        if self.first_report_line_type != "START" or \
           self.last_report_line_type != "REPORT":
            print("Warning: log file may not be consistent")
            print(" started with {}, ended with {}".
                  format(self.first_report_line_type,
                         self.last_report_line_type))
        if self.traceback_found_count:
            print("Warning: {} tracebacks found".
                  format(self.traceback_found_count))
        if self.import_errors_found:
            print("NOTE: python import errors reported.")
        # always do the consistency check
        self.print_consistency_errors()
        for r in self.req_ids:
            self.print_rqst(r, header=False, num_cols=None, indent='')


def summerizer_factory(starter, **kwargs):
    if starter == JSON_STARTER:
        return JsonSummerizer(**kwargs)
    elif starter is REPORT_STARTER:
        return MetricSummerizer(**kwargs)
    elif starter is ANY_STARTER:
        return ExtractSummarizer(**kwargs)
    else:
        raise SystemExit("No summary for '{}' yet".format(starter))


def filter_for_line_type(pattern, lines):
    for l in lines:
        if pattern.match(l):
            yield l


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--json", "-j", dest="starter",
                             action="store_const", const=JSON_STARTER,
                             help='return json lines')
    input_group.add_argument("--report", "-r", dest="starter",
                             action="store_const", const=REPORT_STARTER,
                             help='return billing lines')
    input_group.add_argument("--consistency-check", dest="starter",
                             action="store_const", const=ANY_STARTER,
                             help='find inconsistent request output')
    extract_group = parser.add_mutually_exclusive_group()
    extract_group.add_argument("--extract", help="extract request id's",
                               dest="req_ids", nargs="+")
    extract_group.add_argument("--summarize", action="store_true",
                               help='print summary')
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="add details")
    parser.add_argument("file", help="cloud watch input")
    args = parser.parse_args(argv)

    # Do some munging of args
    if args.starter == ANY_STARTER:
        args.summarize = True
    if args.req_ids:
        args.starter = ANY_STARTER  # process all lines
    return args


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    args = parse_args(argv)
    summary = summerizer_factory(**args.__dict__)
    starter_pattern = re.compile(TIME_STAMP + args.starter, re.VERBOSE)
    for l in filter_for_line_type(starter_pattern, fileinput.input(args.file)):
        summary.add_line(l)
    if args.summarize or args.req_ids:
        summary.print_final_report()


if __name__ == "__main__":
    raise SystemExit(main())
