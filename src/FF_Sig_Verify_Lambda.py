from __future__ import print_function
import boto3
from io import BytesIO

MAX_EXE_SIZE = 100 * (1024 * 1024)  # 100MB


class SigVerifyException(Exception):
    pass


class SigVerifyTooBig(SigVerifyException):
    pass


class SigVerifyBadSignature(SigVerifyException):
    pass

s3 = boto3.resource('s3')


def get_s3_object(bucket_name, key_name):
    s3_object = s3.Object(bucket_name, key_name)
    result = s3_object.get()
    if result['ContentLength'] > MAX_EXE_SIZE:
        msg = """Too big: {}/{} {}
                ({})""".format(bucket_name, key_name, result['ContentLength'],
                               repr(result))
        print(msg)
        raise SigVerifyTooBig(msg)
    obj = BytesIO(result['Body'].read())
    return obj


def check_signature(exe):
    file_len = exe.seek(0, 2)
    msg = "would check {:d} bytes".format(file_len)
    print(msg)
    return False


def report_validity(key, valid):
    if valid:
        msg = "Signature on {} is good.".format(key)
    else:
        msg = "Bad Signature on {}.".format(key)
        raise SigVerifyBadSignature(msg)
    print(msg)


def lambda_handler(event, context):
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        key_name = record['s3']['object']['key']
        print('Processing {}/{}'
              .format(bucket_name, key_name))
        exe_file = get_s3_object(bucket_name, key_name)
        valid_sig = check_signature(exe_file)
        report_validity(key_name, valid_sig)
