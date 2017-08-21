#!/usr/bin/env python

from __future__ import print_function
import collections
import fileinput
import json
import logging
import math
import argparse
import re

# below should probably be a parameter to the app
CONFIGURED_MAX_RUN_TIME_MS = 60 * 1000

JSON_STARTER = '{'
REPORT_STARTER = 'REPORT'

PERF_OUTPUT = """
{invocations:19,d} runs
{total_time_seconds:19,.0f} seconds execution time
{bill_time_seconds:19,.0f} seconds billed
{gb_seconds:19,.0f} GBi seconds (AWS Billing Unit)
{average_time:19,.0f} average milliseconds per run
{max_memory_invocations:19,d} times we used all memory
    {max_memory_pcnt:19.0f}% of runs maxing out memory
    {avg_memory:19,d} MBi average memory used
{max_time_invocations:19,d} times run aborted for excessive time
    {max_time_pcnt:19.0f}% of runs exceeding time limit
    {retry_never_succeeded:19,d} times retry did not succeed
""".strip()

JSON_OUTPUT = """
{pass:6,d} passed
        {Excluded:10,d} exe's not validated
{SigVerifyNoSignature:10,d} exe without signature
{SigVerifyBadSignature:10,d} exe with bad signature
{SigVerifyNonMozSignature:10,d} exe with non-Mozilla signature
        {S3RetrievalFailure:10,d} that couldn't be retrieved from S3
        {S3UnquoteRetry:10,d} that were retried after unquoting
        {S3UnquoteSuccess:10,d} that then succeeded
{other:10,d} other failures
       ---
{fail:6,d} total failed
------
{total:6,d} processed
======
""".strip()

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
    def __init__(self, summarize=False, verbose=False, req_ids=None, **_):
        self.data = []
        self.summarize = summarize
        self.verbose = verbose

    def add_line(self, line):
        if self.summarize:
            datum = json.loads(line.strip())
            self.data.append(datum)
        else:
            print(line, end='')

    def print_final_report(self):
        if self.summarize:
            self.compute_totals()
            print(JSON_OUTPUT.format(**self.counts))
        else:
            for r in self.req_ids:
                print('Log entries for request id {}\n   {}'.
                      format(r, '\n   '.join([x[:80] for x
                                              in self.details[r]])))

    def compute_totals(self):
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
        known_fails = reduce(lambda x, y: x+y, [v for k, v in counts.iteritems()
                                                if k.endswith("Signature")])
        counts['other'] = counts['fail'] - known_fails
        self.counts = counts


class MetricSummerizer(Summerizer):
    """
    Accumulate Metrics from the 'REPORT' text line
    """

    report_pattern = re.compile(r'''  # noqa
                                ^REPORT\s+
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
        self.counts["total_memory"] += float(match.group('mem_used'))
        self.counts["total_allocated_memory"] += \
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
        c["average_time"] = c["total_time"] / c["invocations"]
        c["max_time_pcnt"] = c["max_time_invocations"] * 100 / c["invocations"]
        c["max_memory_pcnt"] = (c["max_memory_invocations"] * 100
                                / c["invocations"])
        c["avg_memory"] = int(math.ceil(c["total_memory"] / c["invocations"]))
        unprocessed = [k for k, v in self.retried_requests.iteritems() if v > 0]
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

    req_id_pattern = re.compile(r'''  # noqa
                                ^\S+\s+  # START, END, or REPORT
                                RequestId:\s+(?P<request_id>\S+).*''',
                                re.VERBOSE)

    def __init__(self, req_ids=None, **_):
        self.req_ids = req_ids or []
        self.details = collections.defaultdict(list)

    def parse(self, line):
        """
        Extract the request id from the given line. The line is either
        json or a report line
        """
        try:
            datum = json.loads(line)
            req_id = datum['request_id']
        except ValueError:
            datum = line.strip()
            match = self.req_id_pattern.search(datum)
            if match:
                req_id = match.group('request_id')
            else:
                # ignore some debug lines
                req_id = None
        return req_id, datum

    def add_line(self, line):
        req_id, datum = self.parse(line)
        if req_id in self.req_ids:
            self.details[req_id].append(datum)

    def print_final_report(self):
        indent = '\n   '
        for r in self.req_ids:
            print("{} had {} log lines.".format(r, len(self.details[r])))
            print(indent[2:], indent.join([str(x)[:80] for x in
                                           self.details[r]]))


def summerizer_factory(starter, **kwargs):
    if starter == JSON_STARTER:
        return JsonSummerizer(**kwargs)
    elif starter is REPORT_STARTER:
        return MetricSummerizer(**kwargs)
    elif starter is "":
        return ExtractSummarizer(**kwargs)
    else:
        raise ValueError("No summary for '{}' yet".format(starter))


def filter_for_line_type(starter, lines):
    for l in lines:
        if l.startswith(starter):
            yield l


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--json", "-j", dest="starter",
                             action="store_const", const=JSON_STARTER,
                             help='return json lines')
    input_group.add_argument("--report", "-r", dest="starter",
                             action="store_const", const=REPORT_STARTER,
                             help='return billing lines')
    extract_group = parser.add_mutually_exclusive_group()
    extract_group.add_argument("--extract", help="extract request id's",
                               dest="req_ids", nargs="+")
    extract_group.add_argument("--summarize", action="store_true",
                               help='print summary')
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="add details")
    parser.add_argument("file", help="cloud watch input")
    args = parser.parse_args(argv)
    if args.req_ids:
        if args.starter != JSON_STARTER:
            parser.error("--extract only valid with --json")
        args.starter = ''  # process all lines
    return args


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    args = parse_args(argv)
    summary = summerizer_factory(**args.__dict__)
    for l in filter_for_line_type(args.starter, fileinput.input(args.file)):
        summary.add_line(l)
    if args.summarize or args.req_ids:
        summary.print_final_report()


if __name__ == "__main__":
    raise SystemExit(main())
