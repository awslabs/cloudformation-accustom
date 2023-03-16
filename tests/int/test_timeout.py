# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Unit Test Library for the Timeout and Chaining Functions
"""
import logging
from pathlib import Path
from unittest import TestCase
from unittest import main as ut_main

import boto3

logging.getLogger().setLevel(logging.DEBUG)

EXECUTED_FILE = f"{Path(__file__).parent}/timeout.executed"
cfn_resource = boto3.resource("cloudformation")


class PreparationTests(TestCase):
    def test_executed_file_exists(self) -> None:
        self.assertTrue(Path(EXECUTED_FILE).is_file())

    def test_stack_status(self) -> None:
        stack_name: str
        with open(EXECUTED_FILE, "r") as f:
            stack_name = f.read().strip()
        stack = cfn_resource.Stack(stack_name)
        self.assertIn(stack.stack_status, ["CREATE_FAILED", "UPDATE_FAILED"])


class TimeoutTests(TestCase):
    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        stack_name: str
        with open(EXECUTED_FILE, "r") as f:
            self.stack_name = f.read().strip()
        self.stack = cfn_resource.Stack(self.stack_name)

    def test_bypass_execution(self) -> None:
        resource = self.stack.Resource("BypassExecution")
        self.assertEqual(resource.resource_status, "CREATE_COMPLETE")

    def test_no_connect_execution(self) -> None:
        resource = self.stack.Resource("NoConnectExecution")
        self.assertEqual(resource.resource_status, "CREATE_FAILED")

    def test_success_execution(self) -> None:
        resource = self.stack.Resource("SuccessExecution")
        self.assertEqual(resource.resource_status, "CREATE_COMPLETE")

    def test_timeout_execution(self) -> None:
        resource = self.stack.Resource("TimeoutExecution")
        self.assertEqual(resource.resource_status, "CREATE_FAILED")

    def test_invalid_properties_execution(self) -> None:
        resource = self.stack.Resource("InvalidPropertiesExecution")
        self.assertEqual(resource.resource_status, "CREATE_FAILED")


if __name__ == "__main__":
    ut_main()
