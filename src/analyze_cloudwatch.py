#!/usr/bin/env python

from __future__ import print_function
import collections
import fileinput
import json
import logging
import optparse
import sys
import re

# below should probably be a parameter to the app
CONFIGURED_MAX_RUN_TIME_MS = 60 * 1000

JSON_STARTER = '{'
REPORT_STARTER = 'REPORT'

PERF_OUTPUT = """
{invocations:19,d} runs
{total_time:19,.0f} milliseconds execution time
{bill_time:19,.0f} milliseconds billed
{average_time:19,.0f} average milliseconds per run
{max_memory_invocations:19,d} times we used all memory
    {max_memory_pcnt:19.0f}% of runs maxing out memory
    {avg_memory:19,d} MBi (not yet computed)
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
    def __init__(self, summarize):
        self.data = []
        self.summarize = summarize

    def add_line(self, line):
        if self.summarize:
            self.data.append(json.loads(line))
        else:
            print(line, end='')

    def print_final_report(self):
        self.compute_totals()
        print(JSON_OUTPUT.format(**self.counts))

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

    def __init__(self, summarize=False):
        self.summarize = summarize
        self.retried_requests = collections.defaultdict(int)
        self.counts = {
            "invocations": 0,
            "total_time": 0,
            "bill_time": 0,
            "average_time": 0,
            "max_memory_invocations": 0,
            "max_memory_pcnt": 0,
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
        if match.group('mem_allocated') == match.group('mem_used'):
            self.counts["max_memory_invocations"] += 1
        rq_id = match.group('request_id')
        if float(match.group('real_time')) >= CONFIGURED_MAX_RUN_TIME_MS:
            self.counts["max_time_invocations"] += 1
            self.retried_requests[rq_id] += 1
            logger.warn("Time exceeded for request {} ('{}')"
                        .format(rq_id, match.group('real_time')))
        elif self.retried_requests[rq_id] > 0:
            logger.warn("Retry successful for request {} (failed {} times)"
                        .format(rq_id, self.retried_requests[rq_id]))
            self.retried_requests[rq_id] -= 1

    def print_final_report(self):
        self.compute_totals()
        print(PERF_OUTPUT.format(**self.counts))

    def compute_totals(self):
        c = self.counts
        c["average_time"] = c["total_time"] / c["invocations"]
        c["max_memory_pcnt"] = (c["max_memory_invocations"] * 100
                                / c["invocations"])
        c["max_time_pcnt"] = c["max_time_invocations"] * 100 / c["invocations"]
        c["retry_never_succeeded"] = len([k for k, v in
                                          self.retried_requests.iteritems() if v
                                          > 0])
        self.counts = c


def summerizer_factory(starter, summarize):
    if starter == JSON_STARTER:
        return JsonSummerizer(summarize)
    elif starter is REPORT_STARTER:
        return MetricSummerizer(summarize)
    elif starter is None:
        return Summerizer()
    else:
        logger.info("No summary for '{}' yet".format(starter))
        return Summerizer()


def filter_for_line_type(starter, lines):
    for l in lines:
        if l.startswith(starter):
            yield l


def parse_args(argv=None):
    parser = optparse.OptionParser()
    parser.add_option("--json", "-j", dest="starter", action="store_const",
                      const=JSON_STARTER, help='return json lines')
    parser.add_option("--report", "-r", dest="starter", action="store_const",
                      const=REPORT_STARTER, help='return billing lines')
    parser.add_option("--summarize", action="store_true",
                      help='print summary')
    args, rest = parser.parse_args(argv)
    if not args.starter:
        parser.error("You must specify an option.")
    return args, rest


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    if argv is None:
        argv = sys.argv
    args, rest = parse_args(argv)
    summary = summerizer_factory(args.starter, args.summarize)
    for l in filter_for_line_type(args.starter, fileinput.input(rest[1:])):
        summary.add_line(l)
    if args.summarize:
        summary.print_final_report()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
