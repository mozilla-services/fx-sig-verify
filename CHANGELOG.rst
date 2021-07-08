Changelog
=========
`0.6.0`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.6.0

*Note: v0.5.x was taken by some abandoned work, so skipped to v0.6.0*

- Update for new Authenticode certificate `bug 1703321`__
- Fix rejection of new timestamp format `issue 89`__
- Update to Python 3.6 `issue 55`__

__ https://bugzilla.mozilla.org/show_bug.cgi?id=1703321
__ https://github.com/mozilla-services/fx-sig-verify/issues/89
__ https://github.com/mozilla-services/fx-sig-verify/issues/55

`0.4.10`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.10

- Update for new Authenticode certificate `bug 1634577`__
__ https://bugzilla.mozilla.org/show_bug.cgi?id=1634577

`0.4.9`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.9

- Update for new Authenticode certificate `bug 1554767`__

- Updated functional AWS testing to work with newer clock skew windows.

__ https://bugzilla.mozilla.org/show_bug.cgi?id=1554767

`0.4.8`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.8

- Bump max binary size (issue GH-54)

- Updated Dockerfile for development to be compatible with current Amazon Linux
  image.

`0.4.7`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.7

- Fix broken tests

`0.4.6`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.6

- NEVER DEPLOYED

- Bump max binary size to accept ASAN builds (issue 46)

`0.4.5`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.5

- Trying new approach to reduce S3 retries.

- Use pytest more better.

- Clean up code per PEP-8.

`0.4.4`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.4

- Fixed `Issue 34`__ - verification should not be done on try builds.

__ https://github.com/mozilla-services/fx-sig-verify/issues/34

`0.4.3`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.3

- Updated build process to work with new AWS Linux Docker Image

`0.4.2`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.2

- Support for the SHA1 code signing cert used on 52esr

- Skip verification for dep build artifacts (they don't use release
  keys)

- ``analyze_cloudwatch`` fixed to report max memory used, as that is the
  meaningful parameter for tuning.

- Various improvements to test cases to avoid regressions.

`0.4.1`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.1

- Change report to show max memory used, rather than average.

- Fix too long SNS Subject lines, `Issue #26`__

__ https://github.com/mozilla-services/fx-sig-verify/issues/26

`0.4.0`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.4.0

-   Support for receiving messages directly from S3 or forwarded from
    SNS. `Issue #28`__.

__ https://github.com/mozilla-services/fx-sig-verify/issues/28

-   Responsibility for excluding non '\*.exe' files moved into lambda
    function to support additional lambda functions needing event
    stream. `Issue #29`__.

__ https://github.com/mozilla-services/fx-sig-verify/issues/29

`0.3.4`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.3.4

-   Catch SNS Publish errors so they do not teminate lambda. They are
    now logged to CloudWatch and the function continues. (Should get
    enough information to fix the errors now.)

-   Makefile reports AWS credentials being used

-   Added 'dev' versioning

    It was too confusing about which version was in stage or dev, and
    how  that differed from prod. Also moved config to setup.cfg (one
    less weird dot-file

-   Added ``get-cloudwatch-logs`` -- bash script to download Cloud Watch
    logs for a lambda function for a specified time range. (Defaults to
    production and all since last log. Can be overridden ``--help`` is
    your friend.)

-   Added ``re-invoke-dirtree`` -- bash script to search for ``.exe``
    files on s3 and invoke the lambda on them. Intednded for backfilling
    when the lambda doesn't work

`0.3.3`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.3.3



-   Clean up S3/Lambda "key" handling

    Old code performed an extra S3 call, but did allow confirmation that the
    ``unquote_plus()`` solution worked. No need for extra calls any more.


-   Improved reporting

    -    Major changes:

           -  Based on the 'REPORT' lines, compute and display metrics
              about number of requests, and usage of memory and CPU
              time.

           -  added ability to extract all AWS & JSON records for a
              request. This report is required to confirm that timed out
              requests were actually retried. (Sometimes the success is
              logged prior to the failure.)

           -  Improved 'exclude' reporting.

              Report now counts how many passes were for exe's that we exclude from validation.

    -    Minor changes:

           -  upgraded from optparse to argparse.
           -  fixed math computations in some places.

-   Activate S3 retry when we detect error. This is experimental, but
    "should" work based on seeing the retries when the system times out.

-   Improved Alerting. Duplicate key info into 'Subject' field of SNS
    message. That gets used if the destination is email. Having a
    default subject made examining the email logs very difficult -- this
    provides more variety in subjects, and thus more (and smaller)
    topics.

`0.3.2`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.3.2

- Only validate certain files in production.

  The entire build tree is pushed to production. That includes several exe
  files that are only used during build, and are not signed at all.

  The choices were to either to:

   a) explicitly exclude the known dev files, or
   b) only include the exes we know we ship.

  This commit uses approach (b), restricting validation to only those we
  expect to ship. This is not fail safe, but I don't have a better
  solution at this time. It can be mitigated by post processing the logs
  on a regular basis.

  Once that filter is in place, it becomes much harder to test. A flag can
  be set to disable the filter, and validate all files. This is fail safe,
  as a wrong setting in production will generate alerts. (Hopefully not at
  0300.)

- Add analysis script for CloudWatch logs. With dev installs,
  ``analyze_cloudwatch`` will be in the path.

- Miscellaneous papercuts bandaged:

      - Disable coveralls until time to fix.
      - Dev environment cleanup with ignores, etc.

`0.3.1`__
-----------------------------------------
__ https://github.com/mozilla-services/fx-sig-verify/tree/v0.3.1

- Pinned pyasn1 to avoid new version with bug__ - it works again!

__ https://github.com/etingof/pyasn1/issues/55

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
