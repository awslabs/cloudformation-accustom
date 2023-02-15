# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Testing of "response" library
"""

from accustom import is_valid_event
from accustom import collapse_data
from accustom import RequestType

from unittest import TestCase, main as ut_main


class ValidEventTests(TestCase):
    def test_missing_field(self):
        event = {
            "RequestType":  RequestType.CREATE,
            "ResponseURL":  "https://test.url",
            "StackId":      None,
            "RequestId":    None,
            "ResourceType": None,
            }
        self.assertFalse(is_valid_event(event))

    def test_no_valid_request_type(self):
        event = {
            "RequestType":       "DESTROY",
            "ResponseURL":       "https://test.url",
            "StackId":           None,
            "RequestId":         None,
            "ResourceType":      None,
            "LogicalResourceId": None
            }
        self.assertFalse(is_valid_event(event))

    def test_invalid_url(self):
        event = {
            "RequestType":       RequestType.CREATE,
            "ResponseURL":       "ftp://test.url",
            "StackId":           None,
            "RequestId":         None,
            "ResourceType":      None,
            "LogicalResourceId": None
            }
        self.assertFalse(is_valid_event(event))

    def test_missing_physical(self):
        event = {
            "RequestType":       RequestType.UPDATE,
            "ResponseURL":       "https://test.url",
            "StackId":           None,
            "RequestId":         None,
            "ResourceType":      None,
            "LogicalResourceId": None
            }
        self.assertFalse(is_valid_event(event))

    def test_included_physical(self):
        event = {
            "RequestType":        RequestType.DELETE,
            "ResponseURL":        "https://test.url",
            "StackId":            None,
            "RequestId":          None,
            "ResourceType":       None,
            "LogicalResourceId":  None,
            "PhysicalResourceId": None
            }
        self.assertTrue(is_valid_event(event))


class CollapseDataTests(TestCase):

    def test_collapse1(self):
        data = {
            "Address": {
                "Street": "Apple Street"
                }

            }
        expected_data = {
            "Address.Street": "Apple Street"
            }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse2(self):
        data = {
            "Address": {
                "Street": "Apple Street",
                "City":   "Fakeville"
                }

            }
        expected_data = {
            "Address.Street": "Apple Street",
            "Address.City":   "Fakeville"
            }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse3(self):
        data = {
            "Address": {
                "Street": "Apple Street",
                "City":   "Fakeville",
                "Number": {
                    "House": 3,
                    "Unit":  18
                    }
                }

            }
        expected_data = {
            "Address.Street":       "Apple Street",
            "Address.City":         "Fakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit":  18
            }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse4(self):
        data = {
            "Address": {
                "Street": "Apple Street",
                "City":   "Fakeville",
                "Number": {
                    "House": 3,
                    "Unit":  18
                    }
                },
            "Name":    "Bob"

            }
        expected_data = {
            "Address.Street":       "Apple Street",
            "Address.City":         "Fakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit":  18,
            "Name":                 "Bob"
            }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse5(self):
        data = {
            "Address":      {
                "Street": "Apple Street",
                "City":   "Fakeville",
                "Number": {
                    "House": 3,
                    "Unit":  18
                    }
                },
            "Address.City": "NotFakeville"

            }
        expected_data = {
            "Address.Street":       "Apple Street",
            "Address.City":         "NotFakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit":  18
            }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)


if __name__ == '__main__':
    ut_main()
