.. _`lambda installation`:
.. _installation-on-aws:

Installation & Testing on AWS Lambda
====================================

Installation
------------

Installation on AWS Lambda requires the following:

    - An AWS Account (free tier should suffice for development)
    - A Lambda function defined
    - SNS & SQS defined & configured for the Lambda function
    - An S3 bucket configured to send events to the Lambda function.
    - A build of the code suitable for deployment on AWS Lambda

Each of these will be covered below.

#.  Create the SNS queue, and note the ARN. Most likely you will also
    want to create an SQS queue to receive and distribute the
    notifications, but that will prevent the function from operating.

#.  Create the Lambda function, and configure it. Remember the function
    must be deployed in the same region that hosts the S3 buckets it
    will process. The following values can be used as a starting point:


    +---------------+------------+-----------------------------------+
    | **container** | Python2.7  |                                   |
    +---------------+------------+-----------------------------------+
    | **memory**    | 128MB      | see log analysis tools to monitor |
    +---------------+------------+-----------------------------------+
    | **timeout**   | 60 seconds |                                   |
    +---------------+------------+-----------------------------------+

    Environment Variables

    +----------+--------------+------------------------------------------------------------------------------------------------------+
    | **Name** | **Required** | **Value**                                                                                            |
    +----------+--------------+------------------------------------------------------------------------------------------------------+
    | SNSARN   | Yes          | The ARN of the SNS queue to be used for notifications                                                |
    +----------+--------------+------------------------------------------------------------------------------------------------------+
    | VERBOSE  | No           | (int) 0 for quiet (default); 1 for notify on all invocations; 2 for trace output in Cloud Watch logs |
    +----------+--------------+------------------------------------------------------------------------------------------------------+

Testing on AWS
--------------

There are test files and ``Makefile`` targets to assist testing:

populate_s3
    This target will prepare an S3 bucket to be used to run the test cases.

invoke-no-error
    This target invokes the lambda function for various files that should
    all be processed without error by the function. (Some files will 'fail'
    verification - that is expected.)

invoke-error
    This target invokes the lambda function for files that are not available
    in the preconfigured S3 bucket. The function should exit cleanly, but
    with an error code and error message.

Parameters for those targets can be entered on the command line, or just
set in the environment:


 ============  ====================================================
  Variable     Usage
 ============  ====================================================
  S3_BUCKET    The bucket to use for testing. It must already exist.
  LAMBDA       The name of the lambda function.
 ============  ====================================================
