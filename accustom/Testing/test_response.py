from accustom import cfnresponse
from accustom import ResponseObject
from accustom import Status
from accustom.Exceptions import DataIsNotDictException
from accustom.Exceptions import NoPhysicalResourceIdException
from accustom.Exceptions import InvalidResponseStatusException
from accustom.Exceptions import FailedToSendResponseException

from unittest import TestCase, main as umain

class cfnresponseTests(TestCase):
    pass

class ResponseObjectTests(TestCase):
    pass

    # TODO: Implement response tests

if __name__ == '__main__':
    umain()