from __future__ import print_function
import boto3
from io import BytesIO
import os
import time

import fx_sig_verify  # noqa: W0611
from verify_sigs import auth_data
from verify_sigs import fingerprint
from verify_sigs import pecoff_blob

# Certificate serial numbers we consider valid
VALID_CERTS = [
    13159122772063869363917814975931229904L,  # just one cert for all channels
]

# simplify debugging - can be set via environ
verbose = False


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


def check_exe(objf):
    """
    Determine if the contents of `objf` are a valid Windows executable signed by
    Mozilla's Authenticode certificate.

    :param objf: a file like object containing the bits to check. The object
        must support a seek() method. The object is never written to.

    :returns boolean: True if object has passed all tests.

    :raises SigVerifyException: if any specific problem is identified in the
        object
    """
    if verbose:
        cur_pos = objf.seek(0, 1)
        len_ = objf.seek(0, 2)
        objf.seek(0, 0)
        print("Processing file of size {} (at {})".format(len_, cur_pos))
    try:
        fingerprinter = fingerprint.Fingerprinter(objf)
        is_pecoff = fingerprinter.EvalPecoff()
        fingerprinter.EvalGeneric()
        results = fingerprinter.HashIt()
    finally:
        objf.close()

    if not is_pecoff:
        msg = 'This is not a PE/COFF binary. Exiting.'
        print(msg)
        raise SigVerifyBadSignature(msg)

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

    # signing_cert_id is a tuple with a last element being the serial number of
    # the certificate. That is a known quantity for our products.
    cert_serial_number = auth.signing_cert_id[-1]
    valid_signature = (auth.has_countersignature and
                       (cert_serial_number in VALID_CERTS)
                       )
    return valid_signature

MAX_EXE_SIZE = 100 * (1024 * 1024)  # 100MB


class SigVerifyException(Exception):
    """
    Catchall for any signature problem found. More specific issues are
    subclasses of SigVerifyException
    """
    pass


class SigVerifyTooBig(SigVerifyException):
    """
    The binary to test is bigger than we expect. This is primarily a test to
    avoid a DoS of this service.
    """
    pass


class SigVerifyBadSignature(SigVerifyException):
    """
    The signature is not valid or not from Mozilla.
    """
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
    if verbose:
        print('Processing {}/{}' .format(bucket_name, key_name))
    exe_file = get_s3_object(bucket_name, key_name)
    valid_sig = check_exe(exe_file)
    report_validity(key_name, valid_sig)


def send_sns(msg, e=None, reraise=False):
    # hack to get traceback in email
    if e:
        import traceback
        msg += traceback.format_exc()
    client = boto3.client("sns")
    # keep a global to prevent infinite recursion on arn error
    global topic_arn
    topic_arn = os.environ.get('SNSARN', "")
    if verbose:
        print("snsarn: {}".format(topic_arn))
    if not topic_arn:
        # bad config, we expected this in the environ
        # set flag so we don't re-raise
        topic_arn = "no-topic-arn"
        raise KeyError("Missing 'SNSARN' from environment")
    response = client.publish(Message=msg, TopicArn=topic_arn)  # noqa: W0612
    if reraise and e:
        raise


def lambda_handler(event, context):
    """
    The main entry point when this package is installed as an AWS Lambda
    Function.

    The determination of validity is always recorded via AWS SNS.

    :param event: a JSON formatted string as described in the AWS Documentation
    :param context: an AWS data structure we do not use.

    :returns None: the S3 event API does not expect any result.
    """
    verbose_override = os.environ.get('VERBOSE')
    if verbose_override:
        global verbose
        verbose = verbose_override
        print("verbose {} based on {}".format(verbose, verbose_override))
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
