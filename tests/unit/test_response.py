# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Testing of "response" library
"""

from unittest import TestCase
from unittest import main as ut_main

from accustom import RequestType, collapse_data, is_valid_event


class ValidEventTests(TestCase):
    def test_missing_field(self) -> None:
        event = {
            "RequestType": RequestType.CREATE,
            "ResponseURL": "https://test.url",
            "StackId": None,
            "RequestId": None,
            "ResourceType": None,
        }
        self.assertFalse(is_valid_event(event))  # type: ignore

    def test_no_valid_request_type(self) -> None:
        event = {
            "RequestType": "DESTROY",
            "ResponseURL": "https://test.url",
            "StackId": None,
            "RequestId": None,
            "ResourceType": None,
            "LogicalResourceId": None,
        }
        self.assertFalse(is_valid_event(event))  # type: ignore

    def test_invalid_url(self) -> None:
        event = {
            "RequestType": RequestType.CREATE,
            "ResponseURL": "ftp://test.url",
            "StackId": None,
            "RequestId": None,
            "ResourceType": None,
            "LogicalResourceId": None,
        }
        self.assertFalse(is_valid_event(event))  # type: ignore

    def test_missing_physical(self) -> None:
        event = {
            "RequestType": RequestType.UPDATE,
            "ResponseURL": "https://test.url",
            "StackId": None,
            "RequestId": None,
            "ResourceType": None,
            "LogicalResourceId": None,
        }
        self.assertFalse(is_valid_event(event))  # type: ignore

    def test_included_physical(self) -> None:
        event = {
            "RequestType": RequestType.DELETE,
            "ResponseURL": "https://test.url",
            "StackId": None,
            "RequestId": None,
            "ResourceType": None,
            "LogicalResourceId": None,
            "PhysicalResourceId": None,
        }
        self.assertTrue(is_valid_event(event))  # type: ignore


class CollapseDataTests(TestCase):
    def test_collapse1(self) -> None:
        data = {"Address": {"Street": "Apple Street"}}
        expected_data = {"Address.Street": "Apple Street"}
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse2(self) -> None:
        data = {"Address": {"Street": "Apple Street", "City": "Fakeville"}}
        expected_data = {"Address.Street": "Apple Street", "Address.City": "Fakeville"}
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse3(self) -> None:
        data = {"Address": {"Street": "Apple Street", "City": "Fakeville", "Number": {"House": 3, "Unit": 18}}}
        expected_data = {
            "Address.Street": "Apple Street",
            "Address.City": "Fakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit": 18,
        }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse4(self) -> None:
        data = {
            "Address": {"Street": "Apple Street", "City": "Fakeville", "Number": {"House": 3, "Unit": 18}},
            "Name": "Bob",
        }
        expected_data = {
            "Address.Street": "Apple Street",
            "Address.City": "Fakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit": 18,
            "Name": "Bob",
        }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)

    def test_collapse5(self) -> None:
        data = {
            "Address": {"Street": "Apple Street", "City": "Fakeville", "Number": {"House": 3, "Unit": 18}},
            "Address.City": "NotFakeville",
        }
        expected_data = {
            "Address.Street": "Apple Street",
            "Address.City": "NotFakeville",
            "Address.Number.House": 3,
            "Address.Number.Unit": 18,
        }
        collapsed_data = collapse_data(data)
        self.assertEqual(expected_data, collapsed_data)


if __name__ == "__main__":
    ut_main()
