from __future__ import print_function
import boto3
from io import BytesIO
import time

import ff_sig_verify  # noqa: W0611
from verify_sigs import auth_data
from verify_sigs import fingerprint
from verify_sigs import pecoff_blob

# Certificate serial numbers we consider valid
VALID_CERTS = [
    13159122772063869363917814975931229904L,
]


# TODO Add proper attribution for code below, and/or move to module

# EVIL EVIL -- Monkeypatch to extend accessor
# TODO(user): This was submitted to pyasn1. Remove when we have it back.
def F(self, idx):
    if type(idx) is int:
        return self.getComponentByPosition(idx)
    else:
        return self.getComponentByName(idx)
from pyasn1.type import univ  # noqa: E402 pylint: disable-msg=C6204,C6203
univ.SequenceAndSetBase.__getitem__ = F
del F, univ
# EVIL EVIL


def print_hashes(results):
    pass


def print_pecoff_hashes(results):
    pass


def print_certificates(auth):
    pass


def check_exe(objf, verbose=False):

    try:
        fingerprinter = fingerprint.Fingerprinter(objf)
        is_pecoff = fingerprinter.EvalPecoff()
        fingerprinter.EvalGeneric()
        results = fingerprinter.HashIt()
    finally:
        objf.close()

    if verbose:
        print_hashes(results)

    if not is_pecoff:
        msg = 'This is not a PE/COFF binary. Exiting.'
        print(msg)
        raise SigVerifyBadSignature(msg)

    if verbose:
        print_pecoff_hashes(results)

    signed_pecoffs = [x for x in results if x['name'] == 'pecoff' and
                      'SignedData' in x]

    if not signed_pecoffs:
        raise auth_data.Asn1Error('This PE/COFF binary has no signature. '
                                  'Exiting.')

    # TODO - can there be multiple signed_pecoffs?
    signed_pecoff = signed_pecoffs[0]
    if verbose and len(signed_pecoffs) > 1:
        print("Found {:d} signed pecoffs. Only processing first "
              "one.".format(len(signed_pecoffs)))

    signed_datas = signed_pecoff['SignedData']
    # There may be multiple of these, if the windows binary was signed multiple
    # times, e.g. by different entities. Each of them adds a complete SignedData
    # blob to the binary.
    # TODO(user): Process all instances
    signed_data = signed_datas[0]
    if verbose and len(signed_datas) > 1:
        print("Found {:d} signed datas. Only processing first "
              "one.".format(len(signed_datas)))

    blob = pecoff_blob.PecoffBlob(signed_data)

    auth = auth_data.AuthData(blob.getCertificateBlob())
    content_hasher_name = auth.digest_algorithm().name
    computed_content_hash = signed_pecoff[content_hasher_name]

    try:
        auth.ValidateAsn1()
        auth.ValidateHashes(computed_content_hash)
        auth.ValidateSignatures()
        auth.ValidateCertChains(time.gmtime())
    except auth_data.Asn1Error:
        if auth.openssl_error:
            print('OpenSSL Errors:\n%s' % auth.openssl_error)
        raise

    # TODO - validate if this is okay for now.
    # base validity on some combo of auth fields.

    if verbose:
        print_certificates(auth)

    # signing_cert_id is a tuple with a last element being the serial number of
    # the certificate. That is a known quantity for our products.
    cert_serial_number = auth.signing_cert_id[-1]
    valid_signature = (auth.has_countersignature and
                       (cert_serial_number in VALID_CERTS)
                       )
    return valid_signature

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


def report_validity(key, valid):
    if valid:
        msg = "Signature on {} is good.".format(key)
    else:
        msg = "Bad Signature on {}.".format(key)
    print(msg)
    if not valid:
        raise SigVerifyBadSignature(msg)


def process_one_s3_file(record):
    bucket_name = record['s3']['bucket']['name']
    key_name = record['s3']['object']['key']
    print('Processing {}/{}' .format(bucket_name, key_name))
    exe_file = get_s3_object(bucket_name, key_name)
    valid_sig = check_exe(exe_file)
    report_validity(key_name, valid_sig)


def send_sns(msg, e=None, reraise=False):
    # hack to get traceback in email
    if e:
        import traceback
        msg += traceback.format_exc()
    # print("attempting to send '{}'".format(msg))
    client = boto3.client("sns")
    response = client.publish(Message=msg,  # noqa: W0612
                              TopicArn="arn:aws:sns:us-west-2:927034868273:hwine-exe-bad")  # noqa: E501
    if reraise and e:
        raise


def lambda_handler(event, context):
    for record in event['Records']:
        try:
            process_one_s3_file(record)
        except SigVerifyBadSignature as e:
            # send SNS of bad binary uploaded
            send_sns("bad sig", e)
        except (SigVerifyTooBig, SigVerifyException) as e:
            # send SNS of program failure
            send_sns("data failure", e)
        except (Exception) as e:
            # uncaught by me program failure
            send_sns("app failure", e)
        else:
            # send SNS of good binary
            # probably should be controlled by environment variable
            send_sns("pass", reraise=False)

if __name__ == '__main__':
    import sys  # noqa: E402
    flo = open(sys.argv[1], 'rb')
    valid = check_exe(flo, True)
    print("file '{}' is {}".format(sys.argv[1], valid))
