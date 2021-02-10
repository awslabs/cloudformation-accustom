# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from accustom import is_valid_event
from accustom import cfnresponse
from accustom import ResponseObject
from accustom import Status
from accustom import RequestType
from accustom.Exceptions import DataIsNotDictException
from accustom.Exceptions import NoPhysicalResourceIdException
from accustom.Exceptions import InvalidResponseStatusException
from accustom.Exceptions import FailedToSendResponseException

import requests_mock
from unittest import TestCase, main as umain

class valid_event_tests(TestCase):
    def test_missing_field(self):
        event = {
            "RequestType" : RequestType.CREATE,
            "ResponseURL" : "https://test.url",
            "StackId" : None,
            "RequestId" : None,
            "ResourceType" : None,
        }
        self.assertFalse(is_valid_event(event))

    def test_no_valid_request_type(self):
        event = {
            "RequestType" : "DESTROY",
            "ResponseURL" : "https://test.url",
            "StackId" : None,
            "RequestId" : None,
            "ResourceType" : None,
            "LogicalResourceId" : None
        }
        self.assertFalse(is_valid_event(event))

    def test_invalid_url(self):
        event = {
            "RequestType" : RequestType.CREATE,
            "ResponseURL" : "ftp://test.url",
            "StackId" : None,
            "RequestId" : None,
            "ResourceType" : None,
            "LogicalResourceId" : None
        }
        self.assertFalse(is_valid_event(event))

    def test_missing_physical(self):
        event = {
            "RequestType" : RequestType.UPDATE,
            "ResponseURL" : "https://test.url",
            "StackId" : None,
            "RequestId" : None,
            "ResourceType" : None,
            "LogicalResourceId" : None
        }
        self.assertFalse(is_valid_event(event))

    def test_included_physical(self):
        event = {
            "RequestType" : RequestType.DELETE,
            "ResponseURL" : "https://test.url",
            "StackId" : None,
            "RequestId" : None,
            "ResourceType" : None,
            "LogicalResourceId" : None,
            "PhysicalResourceId" : None
        }
        self.assertTrue(is_valid_event(event))

class cfnresponseTests(TestCase):
    pass

class ResponseObjectTests(TestCase):
    pass

    # TODO: Implement response tests

if __name__ == '__main__':
    umain()