Summary
=======

The purpose of this code is to validate that binary artifacts used to
install Firefox desktop [#update]_, and distributed by Mozilla are also
signed by Mozilla. (OS level checks only verify the signing was done
properly with an active certificate, but not the publisher.)

The mechanism of the validation varies with the artifact type. There are
the following signing types for the Firefox Desktop applications:

    - Authenticode Code Signing - used for Windows OS ``*.exe`` files.
    - Apple Code Signing - used for macOS ``*.app`` bundles.
    - MAR update signing - used for updates delivered to existing
      Firefox installations.
    - PGP signing - used where a platform standard does not exist (e.g.
      linux).

Authenticode does a pkcs7 signature embedded in the PECOFF structured
``.exe`` file. The certificate associated with the signature can be
traced up certification chain to a root CA. Each certificate has a
unique serial number that can be used to identify it. An ``exe``
artifact passes our validation if all the following apply:

    - the computed hash matches the hash in the signature, and
    - the certificate traces up to a Root CA, and
    - The signature was done within dates the certificate was valid, and
    - The serial number of the certificate matches a "known good" value
      for a certificate issued to Mozilla and intended to be used for
      signing Firefox Desktop executables.

Not all ``exe`` files generated during the build process, and thus
uploaded with the build artifacts, will pass that test. Some internal
tooling must be compiled against the current headers to work correctly.
Thus validation is performed only against ``exe`` files that should be
fully signed -- those that a user will download and execute on their
machine.

Should there ever be an issue detected, Mozilla will not want to
distribute that file until everything is understood about the
discrepancy. To accomplish that task, we examine every ``exe`` uploaded
to the S3 buckets used by the Release Build Process. The initial upload
will precede the actual release by a more-than-sufficient time to
perform all the validations.

Production Deployment
---------------------

The code is packaged as an AWS Lambda function which is triggered by a
"``put``" event on certain S3 buckets. All ``exe`` files are passed to
the function, and the function is responsible for excluding ``exe``
files we do not expect to validate. All invocations of the function are
logged to Cloud Watch with sufficient information to uniquely identify
the operation.

If an unexpected situation is detected, the function generates an AWS
SNS message with sufficient data to identify the severity of the
problem. The SNS message can be routed as desired using standard AWS
tooling.

Local Deployment
---------------------

Operations teams, both for the Lambda function and the Release Build
process, have several common needs:

    - Manually execute the code against a specific artifact.
    - Interpret the log data generated during production.

To support these needs, the ``fx-sig-verify`` python code may be
deployed locally on any machine. [#build_requirements]_ See `cli
installation`__ and :ref:usage for more information.

__ :ref:cli_installation


.. rubric:: Footnotes

.. [#update] Future versions will also validate update artifacts (aka
   "mar files").

.. [#build_requirements] The machine must be capable of running python
   2.7 and building the python M2Crypto library's extensions written in
   C.
