
from fleece import boto3
from fleece.xray import (monkey_patch_botocore_for_xray,
                         trace_xray_subsegment)
# import boto3
from io import BytesIO
import datetime
import json
import os
import subprocess
import tempfile
import time
from typing import Optional
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

import fx_sig_verify

# Certificate serial numbers we consider valid
VALID_CERTS = [
    16100418757095927544930732507868760829,  # new cert bug 1703321
    18436330001563694742140401266315695261,  # new cert bug 1634577
    14785325618211854949562096782187497067,  # new cert bug 1554767
    16384756435581673599510349952793916302,  # new cert bug 1366012
    13159122772063869363917814975931229904,  # just one cert for all channels
    17509195172714594371847083187584920039,  # sha1 cert used for XP on esr
]

# We only want certain extensions handled in production. Originally that was
# handled by the S3 invoking function, but now other consumers want more
# extensions, so we filter here. See
# https://github.com/mozilla-services/fx-sig-verify/issues/29
PRODUCTION_EXTENSIONS = (
    '.exe',
)

# The installers are consistently named. Anything else (as of this writing) is
# some internal tooling that is not distributed to end users.
PRODUCTION_PREFIXES = (
    "Firefox",      # used for Beta & GA releases
    "firefox",      # used for nightly & dep builds
)

# Now that we are handed _all_ the uploads, we do not want to examine try & dep
# builds that go into certain paths
PRODUCTION_KEY_PREFIX_EXCLUSIONS = (
    "/pub/firefox/tinderbox-builds/",
    "/pub/firefox/try-builds/",
)


# We will reject any file larger than this to avoid DoS.
# should not exceed "signcode_maxsize" in RelEng's file:
#   https://github.com/mozilla-releng/build-puppet/blob/master/modules/signingserver/manifests/instance.pp#L16
# bump per:
#   https://github.com/mozilla-releng/build-puppet/pull/410/commits/1a15f279cecc5ed765de7e0327fefe80507f8806
# (while we don't process DLLs at present, we don't want to get caught off
# guard)
MAX_EXE_SIZE = 400 * (1024 * 1024)

# by default wrap all boto calls with x-ray
monkey_patch_botocore_for_xray()


def debug(*args):
    if MozSignedObject.verbose >= 2:
        now = datetime.datetime.utcnow().isoformat()
        for msg in args:
            print("{}: {}".format(now, msg))


class MozSignedObject(object):
    """
    Retain the state and context of the object we're checking. This includes
    the name of the object and the final status.

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
                cls.production_criteria = (False if production_override
                                           else True)
            print(f"production criteria {bool(cls.production_criteria)} based on {production_override}",
                   f"VERBOSE={cls.verbose}")

    @classmethod
    def set_verbose(cls, verbose_override=None):
        cls.set_production_criteria()
        # we only change from the default or current value if specified.
        # verbose_override takes precedence over environment value
        env_value = os.environ.get('VERBOSE')
        if env_value:
            cls.verbose = int(env_value)
        if verbose_override:
            cls.verbose = verbose_override
        print(f"verbose {cls.verbose} based on {env_value} or {verbose_override}")

    def __init__(self, *args, **kwargs):
        self.artifact_name: Optional[str] = None
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
            lines.extend(list(map(indent, self.errors)))
        if self.messages:
            lines.append("other info:")
            lines.extend(list(map(indent, self.messages)))
        return '\n'.join(lines)

    def report_validity(self, valid):
        raise ValueError("report_validity not implemented")

    def get_flo(self, valid=None)-> BytesIO:
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

        # We have 2 criteria for filtering - file extension and file prefix. In
        # both cases, we consider a pass for filtering a 'pass', with the
        # explanation of why.

        # Current criteria is based on prefix of filename. We include the two
        # know good names, rather than exclude the two currently known
        # exceptions (mar.exe & mbsdiff.exe) to reduce false positives (since a
        # invalid exe will page someone).
        basename = os.path.basename(self.artifact_name)
        do_validation = True
        if not basename.endswith(PRODUCTION_EXTENSIONS):
            self.add_message("Excluded from validation by file suffix")
            do_validation = False
        elif not basename.startswith(PRODUCTION_PREFIXES):
            self.add_message("Excluded from validation by file prefix")
            do_validation = False
        else:
            # ignore dependent & try builds, which is based on the first part
            # of the key (in S3 terms), which is the "path" element of an S3
            # url
            url = urllib.parse.urlparse(str(self.artifact_name))
            key = url.path
            if key.startswith(PRODUCTION_KEY_PREFIX_EXCLUSIONS):
                self.add_message("Excluded from validation by key prefix")
                do_validation = False
        return do_validation

    @trace_xray_subsegment()
    def check_exe(self):
        return self.check_exe_new()

    def check_exe_new(self):
        """
        Determine if the contents of `objf` are a valid Windows executable
        signed by Mozilla's Authenticode certificate.

        :returns boolean: True if object has passed all tests.

        :raises SigVerifyException: if any specific problem is identified in
            the object
        """
        def show_output(results) -> None:
            if True:  # TODO: fix MozSignedObject.verbose >= 2:
                if results is None:
                    print("No results from osslsigncode run (likely exception)")
                else:
                    print(f"stdout {type(results.stdout)}; stderr {type(results.stderr)}")
                    print(f"osslsigncode exitcode: {results.returncode}\n"
                        f"-- stderr:\n'{results.stderr}'"
                        f"\n-- stdout\n'{results.stdout}'")

        cert_serial_number = "invalid hex data"
        with self.get_flo() as objf:
            self.show_file_stats(objf)
            # shelling out means we need a real file on disk, so create one
            with tempfile.NamedTemporaryFile(mode="w+b") as real_file:
                print(f"real_file: {dir(real_file)}\n{repr(real_file)}")
                print(f"objf: {dir(objf)}\n{repr(objf)}")
                fname = getattr(real_file, "name", "unknown file name")
                real_file.write(objf.read())
                real_file.flush()
                real_file.seek(0, 0)
                results = None      # needed for linter
                try:
                    results = subprocess.run(["osslsigncode", "verify", fname], universal_newlines=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if results.returncode != 0:
                        # file is badly formed
                        show_output(results)
                        raise SigVerifyBadSignature(f"Corrupted signature in {objf.name}: {results.returncode}")
                    else:
                        show_output(results)
                except Exception as e:
                    print(f"osslsigncode exception {repr(e)}")
                    show_output(results)
                    raise SigVerifyNoSignature
            # parse to get mozilla signature
            for l in [line.strip() for line in results.stdout.splitlines()]:
                # first "Serial" line is for the signature, rest are
                # certificates
                if l.startswith("Serial : "):
                    cert_serial_number = int(l.split(":")[-1].strip(), 16)
                    break
                # the following situation occurs with post balrog stub installers
                # i.e. it shouldn't occur with items uploaded to product
                # delivery
                if l.startswith("Calculated PE checksum:") and l.endswith("MISMATCH!!!!"):
                    show_output(results)
                    raise SigVerifyBadSignature("Checksum Mismatch")
            else:
                show_output(results)
                raise Exception(f"No serial in osslsigncode stdout (len {len(results.stdout)}): '{results.stdout}'")

        valid_signature = cert_serial_number in VALID_CERTS
        if not valid_signature:
            raise SigVerifyNonMozSignature
        return valid_signature


class BytesIOWithName(BytesIO):
    """
    BytesIOWithName - keep track of object's orgininal name

    For better error messages, we want to pass along the orginal name of the object.

    Args:
        original_name (str): name human will recognize
    """
    def __init__(self, *args, original_name:str=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name or "no-name-supplied"

class MozSignedObjectViaLambda(MozSignedObject):
    def __init__(self, bucket=None, key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket_name = bucket
        self.key_name = key
        self.s3_wait_time = 0
        self.artifact_name = "s3://{}/{}".format(bucket, key)

        self.had_s3_error = False
        # S3 is an "eventually consistent" object store. Which leads to the
        # rare, but observed, case where the first S3 get will fail with
        # "NoSuchObject".
        #
        # The good news is S3/Lambda will retry the event 3 times, but IFF the
        # Lambda function fails. We want to catch all errors (if possible), so
        # we can provide better logging. Hence the approach of adding an S3
        # error flag (above), and using that to raise IOError after doing all
        # our reporting (below).
        #
        # This "works well" in practice, as production payloads only contain
        # one S3 event per invocation at this time. However, the event message
        # will show support multiple objects per invocation. Currently, we only
        # use the multi-object mode for testing. If S3 starts using
        # multi-object mode, we would cause retry of all of the objects, not
        # just the failing object. Any problem this might cause will be
        # reported by the analyze_cloudwatch script.

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
            's3wait': self.s3_wait_time,
        }
        return json_info

    @trace_xray_subsegment()
    def get_flo(self):
        s3_client = boto3.client('s3')
        debug("in get_flo")
        start_waiting = time.time()
        try:
            # Make sure the object is really available taken from
            #   https://blog.rackspace.com/the-devnull-s3-bucket-hacking-with-aws-lambda-and-python
            # Don't use defaults, though -- that's 100 sec during testing!
            waiter = s3_client.get_waiter('object_exists')
            waiter.wait(Bucket=self.bucket_name, Key=self.key_name,
                        WaiterConfig={'Delay': 3, 'MaxAttempts': 3})
            result = s3_client.get_object(Bucket=self.bucket_name,
                                          Key=self.key_name)
        except Exception as e:
            debug("s3 exceptions type: {}".format(type(e)))
            self.had_s3_error = True
            text = repr(e)[:256]
            self.add_error("failed to process s3 object {}/{} '{}'"
                           .format(self.bucket_name, self.key_name, text))
            raise
        finally:
            self.s3_wait_time = time.time() - start_waiting

        debug("after s3_client.get_object() result={}".format(type(result)))
        if result['ContentLength'] > MAX_EXE_SIZE:
            msg = """Too big: {}/{} {}
                    ({})""".format(self.bucket_name, self.key_name,
                                   result['ContentLength'], repr(result))
            print(msg)
            raise SigVerifyTooBig(msg)
        debug("before body read")
        flo = BytesIOWithName(result['Body'].read(), original_name=self.key_name)
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
        # use first line of incoming msg as subject, but AWS limit is under 100
        # chars.
        # ASSUME anything over is due to long s3 URL and use heuristic
        subject = msg.split('\n')[0]
        if len(subject) >= 100:
            # split assuming URL, then retain result (index 0) and file name
            # (index -1). File name should be sufficient to allow page
            # recipient to decide urgency of further investigation.
            pieces = subject.split('/')
            subject = "{} ... {}".format(pieces[0], pieces[-1])
            if len(subject) >= 100:
                # don't try to be smarter, full text is still in 'msg'
                subject = "Truncated subject, examine message"

        # append bucket & key, short key first
        msg += "\n{}\nkey={}\nbucket={}".format(
                                            os.path.basename(self.key_name),
                                            self.key_name, self.bucket_name)
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
        try:
            # if the publish fails, we still want to continue, so we get the
            # details into the cloud watch logs. Otherwise, this can
            # (sometimes) terminate the lambda causing retries & DLQ
            response = client.publish(Message=msg, Subject=subject,
                                      TopicArn=topic_arn)
            debug("sns publish: '{}'".format(response))
        except Exception as e:
            self.add_message("sns publish failed\n"
                             "   msg ({}): '{}'\n"
                             "  subj ({}): '{}'\n"
                             "exception: '{}'"
                             "".format(len(msg), str(msg), len(subject),
                                       str(subject), str(e)))


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


def unpacked_s3_events(events, notices=None):
    '''
    Break apart the events structure and yield each S3 record

    :param events: dict with key 'Records' & value a list of sub-events
    :param notices: dict in which to place a note if SNS detected
    :returns s3_event_record: sequence of s3 event records
    '''
    try:
        for event in events['Records']:
            if 's3' in event:
                yield event
            elif 'Sns'in event:
                # embedded events encoded as json string
                if notices:
                    notices['unpacker'] = "SNS message unpacked"
                for inner in unpacked_s3_events(json.loads(
                                                event['Sns']['Message'])):
                    yield inner
            else:
                raise KeyError("unknown event type '{}'"
                               .format(json.dumps(event)))
    except Exception:
        raise ValueError("Invalid AWS Event '{}'".format(json.dumps(events)))


def artifact_to_check_via_s3(lambda_event_record):
    bucket_name = lambda_event_record['s3']['bucket']['name']
    key_name = lambda_event_record['s3']['object']['key']
    # issue #14 - the below decode majik is from AWS sample code.

    real_key_name = urllib.parse.unquote_plus(key_name)
    obj = MozSignedObjectViaLambda(bucket_name, real_key_name)
    return obj


@trace_xray_subsegment()
def lambda_handler(event, context):
    """
    The main entry point when this package is installed as an AWS Lambda
    Function.

    The determination of validity is always recorded via AWS SNS.

    :param event: a JSON formatted string as described in the AWS Documentation
    :param context: an AWS data structure we do not use.

    :returns result: a JSON formatted representation of the action taken. While
                     the AWS lambda interface does not require a return,
                     providing one makes testing and other use cases simpler
    """
    MozSignedObject.set_verbose()
    response = {'version': fx_sig_verify.__version__,
                'input_event': event,
                'request_id': context.aws_request_id,
                }
    results = []
    had_S3_error = False
    for record in unpacked_s3_events(event, response):
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
        had_S3_error = any((had_S3_error, artifact.had_s3_error))
    response['results'] = results
    # always output response to CloudWatch (issue #17)
    # in json format
    # from contextlib import redirect_stdout
    # import sys
    # with redirect_stdout(sys.stderr):
    #     print(json.dumps(response))
    # AWS will retry for us if we fail. So let's do that on an S3 error.
    if had_S3_error:
        # make best effort to get debug info. seems to get lost in container
        # version of lambda
        # TODO: delete flush if it doesn't help with error message
        import sys
        sys.stderr.flush()
        sys.stdout.flush()
        raise IOError("S3 error, try again")
    return response
