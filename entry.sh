#!/bin/bash
if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # running locally, add debug info
    declare -p ${!AWS*} SNSARN VERBOSE PRODUCTION PWD | sed -e 's/\( AWS_SEC\w\+=\)\S\+/\1redacted/g'
    set -x
    exec /usr/bin/aws-lambda-rie /usr/local/bin/python -m awslambdaric $1
else
    exec /usr/bin/env python -m awslambdaric $1
fi
