#!/usr/bin/env python

from __future__ import print_function
import collections
import fileinput
import json
import logging
import optparse
import sys

JSON_STARTER = '{'
REPORT_STARTER = 'REPORT'

JSON_OUTPUT = """
{pass:6,d} passed
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
    def __init__(self):
        self.data = []

    def add_line(self, line):
        self.data.append(json.loads(line))

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
                except IndexError:
                    pass
        # compute uncategorized failures
        known_fails = reduce(lambda x, y: x+y, [v for k, v in counts.iteritems()
                                                if k.endswith("Signature")])
        counts['other'] = counts['fail'] - known_fails
        self.counts = counts


def summerizer_factory(starter):
    if starter == JSON_STARTER:
        return JsonSummerizer()
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
    if argv is None:
        argv = sys.argv
    args, rest = parse_args(argv)
    summary = summerizer_factory(args.starter)
    for l in filter_for_line_type(args.starter, fileinput.input(rest[1:])):
        summary.add_line(l)
    if args.summarize:
        summary.print_final_report()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    raise SystemExit(main(sys.argv))
