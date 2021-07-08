"""
Module that contains the command line app.

Assumed to be called with one command line argument -- the file to be checked.
When called from the command line, the SigVerifyTooBig exception is not raised.


Layout based on https://github.com/ionelmc/cookiecutter-pylibrary
"""

import argparse
import subprocess
import sys
# set up path for everything else
import fx_sig_verify
from fx_sig_verify.validate_moz_signature import (MozSignedObject,
                                                  SigVerifyException)


class MozSignedObjectViaCLI(MozSignedObject):
    def __init__(self, fname=None, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.artifact_name = fname
        self.url = "file://{}".format(fname)

    def get_location(self):
        "For S3, we need the bucket & key names"
        return self.bucket, self.key

    def report_validity(self, valid):
        """
        For invoked cli functions, we have 2 report channels:
            1. print to stdout
            2. exit code

        The severity of any failure controls the what & where.
        Any filtering or special casing should probably be applied in this
        function. (E.g. excluding any artifacts from rules.)
        """
        if self.verbose:
            print(self.format_message())

    def summary(self):
        json_info = {
            'bucket': self.bucket_name,
            'key': self.key_name,
            'status': self.get_status(),
            'results': self.errors + self.messages,
        }
        return json_info

    def get_flo(self):
        flo = open(self.artifact_name, 'rb')
        return flo

    def process_one_local_file(self):
        if self.verbose:
            print('Processing {}'.format(self.artifact_name))
        try:
            valid_sig = self.check_exe()
        except Exception as e:
            valid_sig = False
            if isinstance(e, SigVerifyException):
                self.add_error("Exception {}".format(type(e).__name__))
            else:
                self.add_error("failed to process local file {} '{}'"
                               .format(self.artifact_name, repr(e)))
        self.set_status("pass" if valid_sig else "fail")
        return valid_sig


def parse_args(cmd_line=None):
    parser = argparse.ArgumentParser(description='Check executable validity.')
    parser.add_argument('--version', action='version',
                        version="%(prog)s " + fx_sig_verify.__version__,
                        help='print version and exit')
    parser.add_argument('suspect', help='file to check for validity',
                        nargs=1)
    args = parser.parse_args(cmd_line)
    return args


def main(cmd_line=None):
    """
    Check if the file specified on the command line is a valid Mozilla
    executable for Windows

    :param filename: path to ``exe`` file
    :returns result_code: 0 if no failure, per unix conventions
    """
    MozSignedObject.set_verbose(True)
    MozSignedObject.set_production_criteria(False)
    found_bad_file = False
    args = parse_args(cmd_line=cmd_line)
    for arg in args.suspect:
        artifact = MozSignedObjectViaCLI(arg)
        try:
            valid = artifact.process_one_local_file()
        except SigVerifyException:
            valid = False
        artifact.report_validity(valid)
        if not valid:
            found_bad_file = True
    raise SystemExit(1 if found_bad_file else 0)

if __name__ == "__main__":
    main(sys.argv[1:])
