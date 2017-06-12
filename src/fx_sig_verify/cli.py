"""
Module that contains the command line app.

Assumed to be called with one command line argument -- the file to be checked.
When called from the command line, the SigVerifyTooBig exception is not raised.


Layout based on https://github.com/ionelmc/cookiecutter-pylibrary
"""
import argparse
# set up path for everything else
from fx_sig_verify.validate_moz_signature import check_exe


# TODO(hwine@mozilla.com): provide real command line args.
parser = argparse.ArgumentParser(description='Command description.')
parser.add_argument('names', metavar='NAME', nargs=argparse.ZERO_OR_MORE,
                    help="A name of something.")


def main(args=None):
    """
    Check if the file specified on the command line is a valid Mozilla
    executable for Windows

    :param filename: path to ``exe`` file
    :returns result_code: 0 if no failure, per unix conventions
    """
    args = parser.parse_args(args=args)
    flo = file(args.names[0], 'rb')
    valid = check_exe(flo)
    raise SystemExit(0 if valid else 1)
