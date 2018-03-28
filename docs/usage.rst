=====
Usage
=====

To use fx-sig-verify in a project::

	import fx_sig_verify


There are also some locally useful utilities which can be installed. At
the command line::

    pip install fx-sig-verify[cli]

That provides the following scripts:

``fx-sig-verify``:
    Command line version of the lambda function. Can be used to check
    local files. It outputs the pass/fail status of the file.

``get-cloudwatch-logs``:
    Downloads Cloud Watch logs for a given date range. These can be
    processed further, usually by ``analyze_cloudwatch``. Use the
    ``--help`` option for more information on usage.

``analyze_cloudwatch``:
    Performs analysis on local copies of the CloudWatch logs generated
    by the lambda function. It can perform simple analysis, or extract
    lines of interest for further processing. Use the ``--help`` option
    for more information on usage. Common invocations include:

    - ``analyze_cloudwatch --report --summarize _{logfile}_``

        outputs usage information from an AWS (billing) perspective.
        Includes max memory used size for tuning lambda parameters.

    -  ``analyze_cloudwatch --json --summarize _{logfile}_``

        Outputs usage information from a functional perspective. I.e.
        how many files checked, etc.

``print-pe-certs``:
    This script is from the original code, and is the source of the
    logic for the lambda function. It will print out the certificate
    chain for any file. This can be very useful for debugging.

print-pe-certs
--------------

This script is from the `original source`__. It prints the certificate
metadata and calculated hashes from the supplied ``exe`` file. This is
useful for determining the exact validation cause.

fx-sig-verify
-------------

This executes the production code from the command line. The primary
difference is the return values are not in the JSON format. An exit code
of not-zero is used for any failure, so the script can be used from
other scripts.

analyze_cloudwatch
------------------

In production, the primary logging is done to Cloud Watch. This script
analyzes raw Cloud Watch logs (downloaded via a utility like awslogs__).
Cloud Watch logs for lambda function contain 2 types of information: AWS invocation
logging (when, ID, resource usage) as plain text records, and any
information written to standard out by the Lambda function. Currently,
the function outputs JSON for invocation status, and plain text for
debug records.

__ https://github.com/jorgebastida/awslogs

The script performs 2 functions:

    - extracts either the billing or invocation status records for
      further processing
    - provides a brief summary of either type.

__ :ref:`base library`
