Changelog
=========

`0.3.0`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.3.0

  - CloudWatch logs in json, limited length. Breaks prior analysis
    scripts.

  - CloudWatch logs not being in json make the log analysis too hard. This
    will change yet again as it's moved into mozlog format.

  - Also, on S3 failures, logging the exception text (repr()) generated
    extremely large log messages. These exceeded the max allowed length of
    256K bytes! Now those messages are truncated to 256 characters.

  - Set more complete offline test environment

`0.2.6`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.6

 - Improve test coverage to actually test the case from issue `#14`__

 - Fix the code that the new tests uncovered.

__ https://github.com/mozilla-services/fx-sig-verify/issues/14

`0.2.5`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.5

 - Changed approach to unescaping 'key' provided by S3.

 - Added AWS Request ID and event record to logging. Request ID needed
   to correlate invocation when multiple log streams combined.

 - Removed the 5 second backoff from 0.2.4 - it did nothing.

`0.2.4`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.4

 - Add a 5 second backoff if we get NoSuchKey from S3. And instrument
   the logs output to be able to detect efficacy.

`0.2.3`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.3

 - Always send SNS on failure. It was bustage from Refactoring
   (04d8e926c). No test case for fail path alerting.

 - Also removed redundant test_lambda_call.py, which was done prior to use
   of moto.

`0.2.2`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.2

- [issue `#17`__] 'pass' messages are always logged to CloudWatch

__ https://github.com/mozilla-services/fx-sig-verify/issues/17

`0.2.1`__ (2017-07-13)
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.1

- [issue `#13`__] 'pass' messages are no longer sent to SNS, unless in verbose mode

__ https://github.com/mozilla-services/fx-sig-verify/issues/13

`0.2.0`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.2.0

- Support for new Authenticode cert `bug 1366012`__

__ https://bugzilla.mozilla.org/show_bug.cgi?id=1366012

0.1.1
-----------------------------------------

- Initial deployment for production environment (without automated
  alerting)

0.1.0 (2017-04-13)
-----------------------------------------

- Initial deployment for staging.


