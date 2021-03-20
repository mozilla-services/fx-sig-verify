import pytest
import os
import boto3

# Constants
bucket_name = 'pseudo-bucket'
sqs_name = "test-queue"


class DummyContext(object):
    aws_request_id = 'DUMMY ID'


dummy_context = DummyContext()


def not_in(text, array, array2=None):
    # return true if text is not in any element of the array
    result = True
    for line in array:
        if array2:
            for l2 in line[array2]:
                if text in l2:
                    result = False
                    break
        elif text in line:
            result = False
        if not result:
            break
    return result


def is_in(text, array, array2=None):
    return not not_in(text, array, array2)


@pytest.fixture(scope='session', autouse=True)
def set_valid_region():
    # moto requires valid region, even though not sending anything
    os.environ['AWS_DEFAULT_REGION'] = "us-east-1"
    # make sure a profile doesn't mess us up
    try:
        del os.environ['AWS_DEFAULT_PROFILE']
    except KeyError:
        pass


def build_event(bucket, key):
    record = {'s3': {'bucket': {'name': bucket},
                     'object': {'key': key},
                     },
              }
    return {'Records': [record, ]}


bad_key_names_list = [
    'bad_1.exe',
    'bad_1.mar',
    "Firefox",
    "firefox",
]
# all need to have valid suffix now
good_key_names_list = [
    "Firefox.exe",
    "Firefox sadf asfsd.exe",
    "firefox.exe",
    "firefox-asdjsll.exe",
    "nightly/fred/firefox-asdkjds.exe",
    "release/sam/Firefox asdfe sss.exe",
]


bad_file_names_list = ['bad_1.exe', ]


good_file_names_list = [
    '32bit.exe',  # signed with older valid key
    '32bit_new.exe',  # signed with current valid key
    '2019-06-64bit.exe', # cert valid since bug 1554767
    '2020-05-32bit.exe', # cert valid since bug 1634577
    'FxSetup-87.0b2.exe',  # signed with sha2 timestamp issue 89
]


def delete_verbose():
    try:
        del os.environ['VERBOSE']
    except KeyError:
        pass


def zero_verbose():
    os.environ['VERBOSE'] = '0'


def unset_verbose():
    os.environ['VERBOSE'] = ''


set_verbose_false_list = [
    delete_verbose,
    zero_verbose,
    unset_verbose
]


def one_verbose():
    os.environ['VERBOSE'] = '1'


def two_verbose():
    # 2 is debug level
    os.environ['VERBOSE'] = '2'


set_verbose_true_list = [
    one_verbose,
    two_verbose,
]


def delete_production():
    try:
        del os.environ['PRODUCTION']
    except KeyError:
        pass


def zero_production():
    os.environ['PRODUCTION'] = '0'


def unset_production():
    os.environ['PRODUCTION'] = ''


set_production_false_list = [
    zero_production,
]


def true_production():
    os.environ['PRODUCTION'] = '1'


set_prod_true_list = [
    delete_production,
    true_production,
    unset_production
]


def create_bucket():
    conn = boto3.resource('s3', region_name='us-east-1')
    bucket = conn.create_bucket(Bucket=bucket_name)
    return bucket


def upload_file(bucket, filename, key_name=None):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    fname = os.path.join(data_dir, filename)
    # to replicate S3 functionality, change any space in file name to a '+'
    # see issue #14
    if not key_name:
        # if a keyname isn't specified, build one
        key_name = filename.replace(' ', '+')
    bucket.put_object(Body=open(fname, 'rb'), Key=key_name)
    return (bucket_name, key_name)


def setup_aws_mocks():
    # mock the SNS topic & pass via environment
    client = boto3.client("sns")
    client.create_topic(Name="some-topic")
    response = client.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']
    os.environ['SNSARN'] = topic_arn

    # setup an sqs queue to pull the message from
    sqs_conn = boto3.resource('sqs', region_name='us-east-1')
    sqs_conn.create_queue(QueueName=sqs_name)

    client.subscribe(TopicArn=topic_arn,
                     Protocol="sqs",
                     Endpoint="arn:aws:sqs:us-east-1:123456789012:test-queue")
    queue = sqs_conn.get_queue_by_name(QueueName=sqs_name)
    return queue


def get_one_message(queue):
    # get more than one to detect double push
    messages = queue.receive_messages(MaxNumberOfMessages=10)
    return (len(messages), messages[0].body) if len(messages) else (0, '')
