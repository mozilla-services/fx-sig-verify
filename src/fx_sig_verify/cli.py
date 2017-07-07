"""
Module that contains the command line app.

Assumed to be called with one command line argument -- the file to be checked.
When called from the command line, the SigVerifyTooBig exception is not raised.


Layout based on https://github.com/ionelmc/cookiecutter-pylibrary
"""
from __future__ import print_function
import argparse
# set up path for everything else
import fx_sig_verify
from fx_sig_verify.validate_moz_signature import (check_exe, report_validity,
                                                  SigVerifyException,
                                                  set_verbose)


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
    set_verbose(True)
    args = parse_args(cmd_line=cmd_line)
    flo = file(args.suspect[0], 'rb')
    try:
        valid = check_exe(flo)
        report_validity(args.suspect[0], valid)
    except SigVerifyException:
        valid = False
        pass
    raise SystemExit(0 if valid else 1)
