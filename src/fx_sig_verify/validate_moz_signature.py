from __future__ import print_function
from fleece import boto3
from fleece.xray import (monkey_patch_botocore_for_xray,
                         trace_xray_subsegment)
# import boto3
from io import BytesIO
import datetime
import json
import os
import time
import urllib

import fx_sig_verify
from verify_sigs import auth_data
from verify_sigs import fingerprint
from verify_sigs import pecoff_blob

# Certificate serial numbers we consider valid
VALID_CERTS = [
    16384756435581673599510349952793916302L,  # new cert bug 1366012
    13159122772063869363917814975931229904L,  # just one cert for all channels
]

# We will reject any file larger than this to avoid DoS.
MAX_EXE_SIZE = 100 * (1024 * 1024)  # 100MiB

# by default wrap all boto calls with x-ray
monkey_patch_botocore_for_xray()


def debug(*args):
    if MozSignedObject.verbose >= 2:
        now = datetime.datetime.utcnow().isoformat()
        for msg in args:
            print("{}: {}".format(now, msg))


# EVIL EVIL -- Monkeypatch to extend accessor
# This patch is part of the google code, and must be set before calling any of
# the analysis routines. See the verify_sigs directory for license information.
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


class MozSignedObject(object):
    """
    Retain the state and context of the object we're checking. This includes the
    name of the object and the final status.

    Sub class for different conventions on name and status reporting.
    """

    # simplify debugging - can be set via environ
    verbose = 0
    production_criteria = True

    @classmethod
    def set_production_criteria(cls, production_override=None):
        # reset - testing issue, not production, as new class isn't created
        cls.production_criteria = True
        if production_override is None:
            production_override = os.environ.get('PRODUCTION')
            print('PRODUCTION={}'.format(production_override))
        if production_override is not None:
            try:
                cls.production_criteria = int(production_override)
            except ValueError:
                cls.production_criteria = False if production_override else True
            print("production criteria {} based on {}"
                  .format(bool(cls.production_criteria), production_override))

    @classmethod
    def set_verbose(cls, verbose_override=None):
        cls.set_production_criteria()
        # reset - testing issue, not production, as new class isn't created
        cls.verbose = 0
        if not verbose_override:
            verbose_override = os.environ.get('VERBOSE')
        if verbose_override:
            try:
                cls.verbose = int(verbose_override)
            except ValueError:
                cls.verbose = 1 if verbose_override else 0
            print("verbose {} based on {}".format(cls.verbose,
                                                  verbose_override))

    def __init__(self, *args, **kwargs):
        self.artifact_name = None
        self.object_status = None
        self.errors = []
        self.messages = []
        if args or kwargs:
            raise TypeError("unexpected args")

    def set_status(self, new_status, only_if_unset=False):
        if self.object_status and only_if_unset:
            debug("ignoring '{}', already '{}'".format(new_status,
                                                       self.object_status))
            return  # # Early Exit
        if self.object_status and not only_if_unset:
            #  changing -- keep track
            msg = ("changing status from '{}' to '{}'"
                   .format(self.object_status, new_status))
            debug(msg)
            self.add_message(msg)
        self.object_status = new_status

    def get_status(self):
        if not self.object_status:
            raise ValueError("subclass failed to status object")
        return self.object_status

    def as_dict(self):
        "handy method to reference various instance vars in format() calls"
        return self.__dict__

    def add_error(self, *args):
        self.errors.extend(args)

    def add_message(self, *args):
        self.messages.extend(args)

    def format_message(self):

        def indent(s):
            return '    ' + str(s)
        lines = []
        lines.append("{} for {}".format(self.get_status(), self.artifact_name))
        if self.errors:
            lines.append("errors:")
            lines.extend(map(indent, self.errors))
        if self.messages:
            lines.append("other info:")
            lines.extend(map(indent, self.messages))
        return '\n'.join(lines)

    def report_validity(self, valid):
        raise ValueError("report_validity not implemented")

    def get_flo(self, valid):
        raise ValueError("get_flo not implemented")

    def show_file_stats(self, objf):
        if self.verbose:
            cur_pos = objf.tell()
            objf.seek(0, 2)
            len_ = objf.tell()
            objf.seek(0, 0)
            print("Processing file of size {} (at {})".format(len_, cur_pos))

    def should_validate(self):
        """
        Filter out any items that should not be checked. Decision is made on
        information already in the object.
        """
        if not self.production_criteria:
            # We're in test mode, process everything
            return True

        # Current criteria is based on prefix of filename. We include the two
        # know good names, rather than exclude the two currently known
        # exceptions (mar.exe & mbsdiff.exe) to reduce false positives (since a
        # invalid exe will page someone).
        def startswithoneof(fname, prefixes):
            result = False
            for prefix in prefixes:
                if fname.startswith(prefix):
                    result = True
                    break
            return result

        allowed_prefixes = [
            "Firefox",      # used for Beta & GA releases
            "firefox",      # used for nightly & dep builds
        ]
        basename = os.path.basename(self.artifact_name)
        do_validation = startswithoneof(basename, allowed_prefixes)
        if not do_validation:
            self.add_message("Excluded from validation by prefix")
        return do_validation

    @trace_xray_subsegment()
    def check_exe(self):
        """
        Determine if the contents of `objf` are a valid Windows executable
        signed by Mozilla's Authenticode certificate.

        This code mostly lifted from
            src/fx_sig_verify/verify_sigs/print_pe_certs.py

        with print statements removed :)

        :returns boolean: True if object has passed all tests.

        :raises SigVerifyException: if any specific problem is identified in the
            object
        """
        objf = self.get_flo()
        self.show_file_stats(objf)
        try:
            fingerprinter = fingerprint.Fingerprinter(objf)
            is_pecoff = fingerprinter.EvalPecoff()
            fingerprinter.EvalGeneric()
            results = fingerprinter.HashIt()
        except Exception as e:
            raise SigVerifyNoSignature(e)
        finally:
            objf.close()

        if not is_pecoff:
            msg = 'This is not a PE/COFF binary. Exiting.'
            print(msg)
            raise SigVerifyNoSignature(msg)

        signed_pecoffs = [x for x in results if x['name'] == 'pecoff' and
                          'SignedData' in x]

        if not signed_pecoffs:
            msg = 'This PE/COFF binary has no signature. Exiting.'
            raise SigVerifyNoSignature('This PE/COFF binary has no signature. '
                                       'Exiting.')

        # TODO - can there be multiple signed_pecoffs?
        signed_pecoff = signed_pecoffs[0]
        if len(signed_pecoffs) > 1:
            msg = ("Found {:d} signed pecoffs. Only processing first "
                   "one.".format(len(signed_pecoffs)))
            self.add_message(msg)
            if self.verbose:
                print(msg)

        signed_datas = signed_pecoff['SignedData']
        # There may be multiple of these, if the windows binary was signed
        # multiple times, e.g. by different entities. Each of them adds a
        # complete SignedData blob to the binary.
        # TODO(user): Process all instances
        signed_data = signed_datas[0]
        if self.verbose and len(signed_datas) > 1:
            msg = ("Found {:d} signed datas. Only processing first "
                   "one.".format(len(signed_datas)))
            self.add_message(msg)
            if self.verbose:
                print(msg)
            msg = "Multiple Signatures"
            raise SigVerifyBadSignature(msg)

        blob = pecoff_blob.PecoffBlob(signed_data)

        auth = auth_data.AuthData(blob.getCertificateBlob())
        content_hasher_name = auth.digest_algorithm().name
        computed_content_hash = signed_pecoff[content_hasher_name]

        try:
            auth.ValidateAsn1()
            auth.ValidateHashes(computed_content_hash)
            auth.ValidateSignatures()
            auth.ValidateCertChains(time.gmtime())
        except auth_data.Asn1Error as e:
            if auth.openssl_error:
                msg = 'OpenSSL Errors:\n%s' % auth.openssl_error
                self.add_error(msg)
            else:
                msg = 'Asn1Error: {}'.format(str(e))
            raise SigVerifyBadSignature(msg)

        # TODO - validate if this is okay for now.
        # base validity on some combo of auth fields.

        # signing_cert_id is a tuple with a last element being the serial number
        # of the certificate. That is a known quantity for our products.
        cert_serial_number = auth.signing_cert_id[-1]
        valid_signature = (auth.has_countersignature and (cert_serial_number in
                                                          VALID_CERTS))
        if not valid_signature:
            raise SigVerifyNonMozSignature
        return valid_signature


class MozSignedObjectViaLambda(MozSignedObject):
    def __init__(self, bucket=None, key=None, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.bucket_name = bucket
        self.key_name = key
        self.artifact_name = "s3://{}/{}".format(bucket, key)

    def get_location(self):
        "For S3, we need the bucket & key names"
        return self.bucket_name, self.key_name

    def report_validity(self, valid=None):
        """
        For invoked lambda functions, we have 3 report channels:
            1. print to stdout (will end up in  CloudWatch logs)
            2. send message to SNS
            3. return JSON blob as function result (for testing)

        The severity of any failure controls the what & where.
        Any filtering or special casing should probably be applied in this
        function. (E.g. excluding any artifacts from rules.)
        """
        message = self.format_message()
        if valid is None:
            # Infer validity from message
            valid = message.startswith('pass')
        if self.verbose:
            print("msg: '{}'".format(message))
            print("sum: '{}'".format(self.summary()))
        if (not valid) or self.verbose:
            self.send_sns(message)

    def summary(self):
        debug("len errors {},  messages {}".format(len(self.errors),
                                                   len(self.messages)))
        json_info = {
            'bucket': self.bucket_name,
            'key': self.key_name,
            'status': self.get_status(),
            'results': self.errors + self.messages,
        }
        return json_info

    @trace_xray_subsegment()
    def get_flo(self):
        s3_client = boto3.client('s3')
        debug("in get_flo")
        try:
            result = s3_client.get_object(Bucket=self.bucket_name,
                                          Key=self.key_name)
        except Exception as e:
            text = repr(e)[:256]
            self.add_error("failed to process s3 object {}/{} '{}'"
                           .format(self.bucket_name, self.key_name, text))
            # issue #14 - the below decode majik is from AWS sample code.
            new_key = urllib.unquote_plus(self.key_name.encode('utf8'))
            self.add_message("First get failed ({}), trying to unquote"
                             " ({})".format(self.key_name, new_key))
            result = s3_client.get_object(Bucket=self.bucket_name,
                                          Key=new_key)
            self.add_message("get_object worked after unescaping")

        debug("after s3_client.get_object() result={}".format(type(result)))
        if result['ContentLength'] > MAX_EXE_SIZE:
            msg = """Too big: {}/{} {}
                    ({})""".format(self.bucket_name, self.key_name,
                                   result['ContentLength'], repr(result))
            print(msg)
            raise SigVerifyTooBig(msg)
        debug("before body read")
        flo = BytesIO(result['Body'].read())
        debug("after read() flo={}".format(type(flo)))
        return flo

    @trace_xray_subsegment()
    def process_one_s3_file(self):
        if self.verbose:
            print('Processing {}' .format(self.artifact_name))
        valid_sig = True
        try:
            if self.should_validate():
                valid_sig = self.check_exe()
        except Exception as e:
            valid_sig = False
            if isinstance(e, SigVerifyException):
                self.add_error("Failure reason: {}".format(type(e).__name__))
            else:
                text = repr(e)[:256]
                self.add_error("failed to process s3 object {}/{} '{}'"
                               .format(self.bucket_name, self.key_name,
                                       text))
        self.set_status("pass" if valid_sig else "fail", only_if_unset=True)
        return valid_sig

    @trace_xray_subsegment()
    def send_sns(self, msg, e=None, reraise=False):
        # hack to get traceback in email
        if e:
            import traceback
            msg += traceback.format_exc()
        client = boto3.client("sns")
        # keep a global to prevent infinite recursion on arn error
        global topic_arn
        topic_arn = os.environ.get('SNSARN', "")
        if self.verbose:
            print("snsarn: {}".format(topic_arn))
        if not topic_arn:
            # bad config, we expected this in the environ
            # set flag so we don't re-raise
            topic_arn = "no-topic-arn"
            raise KeyError("Missing 'SNSARN' from environment")
        response = client.publish(Message=msg, TopicArn=topic_arn)  # noqa: W0612


class SigVerifyException(Exception):
    """
    Catchall for any signature problem found. More specific issues are
    subclasses of SigVerifyException
    """
    pass


class SigVerifyTooBig(SigVerifyException):
    """
    The binary to test is bigger than we expect. This is primarily a test to
    avoid a DoS of this service. However, since we only expect to be called for
    valid executables, this is still an anomaly.
    """
    pass


class SigVerifyNonMozSignature(SigVerifyException):
    """
    An valid signed ".exe" file, but not signed by Mozilla.
    """
    pass


class SigVerifyNoSignature(SigVerifyException):
    """
    An unsigned ".exe" file.
    """
    pass


class SigVerifyBadSignature(SigVerifyException):
    """
    The signature is not valid or not from Mozilla.
    """
    pass


def artifact_to_check_via_s3(lambda_event_record):
    bucket_name = lambda_event_record['s3']['bucket']['name']
    key_name = lambda_event_record['s3']['object']['key']
    obj = MozSignedObjectViaLambda(bucket_name, key_name)
    return obj


@trace_xray_subsegment()
def lambda_handler(event, context):
    """
    The main entry point when this package is installed as an AWS Lambda
    Function.

    The determination of validity is always recorded via AWS SNS.

    :param event: a JSON formatted string as described in the AWS Documentation
    :param context: an AWS data structure we do not use.

    :returns None: the S3 event API does not expect any result.
    """
    MozSignedObject.set_verbose()
    response = {'version': fx_sig_verify.__version__,
                'input_event': event,
                'request_id': context.aws_request_id,
                }
    results = []
    for record in event['Records']:
        artifact = artifact_to_check_via_s3(record)
        try:
            valid_sig = False
            try:
                valid_sig = artifact.process_one_s3_file()
                debug("after process 1 {}".format(valid_sig))
            except SigVerifyNonMozSignature as e:
                msg = "non-moz signature"
                debug(msg)
                artifact.send_sns(msg, e)
            except SigVerifyTooBig as e:
                # send SNS of program failure
                msg = "data failure"
                debug(msg)
                artifact.send_sns(msg, e)
            except SigVerifyNoSignature as e:
                msg = "exe without sig"
                debug(msg)
                artifact.send_sns(msg, e)
            except SigVerifyBadSignature as e:
                # send SNS of bad binary uploaded
                msg = "bad sig"
                debug(msg)
                artifact.send_sns(msg, e)
            except SigVerifyException as e:
                msg = "unclassified error"
                debug(msg)
                artifact.send_sns(msg, e)
            except (Exception) as e:
                # uncaught by me program failure
                msg = ("app failure: " + str(type(e).__name__) +
                       str(repr(e)))
                debug(msg)
                artifact.send_sns(msg, e)
        except (Exception) as e:
            # double exception, should already have a message
            artifact.add_error("app failure 2: {}".format(str(e)))
        artifact.report_validity()
        results.append(artifact.summary())
    response['results'] = results
    # always output response to CloudWatch (issue #17)
    # in json format
    print(json.dumps(response))
    return response
