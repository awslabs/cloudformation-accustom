# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Unit Test Library for the Redaction Processes
"""
import json
import logging
from pathlib import Path
from typing import List
from unittest import TestCase
from unittest import main as ut_main

import boto3
from mypy_boto3_cloudformation.service_resource import CloudFormationServiceResource, Stack
from mypy_boto3_logs.client import CloudWatchLogsClient
from mypy_boto3_logs.paginator import FilterLogEventsPaginator
from mypy_boto3_logs.type_defs import FilterLogEventsResponseTypeDef

logging.getLogger().setLevel(logging.DEBUG)

EXECUTED_FILE = f"{Path(__file__).parent}/redact.executed"
cfn_resource: CloudFormationServiceResource = boto3.resource("cloudformation")
logs_client: CloudWatchLogsClient = boto3.client("logs")
log_events_paginator: FilterLogEventsPaginator = logs_client.get_paginator("filter_log_events")


class PreparationTests(TestCase):
    def test_executed_file_exists(self) -> None:
        self.assertTrue(Path(EXECUTED_FILE).is_file())

    def test_stack_status(self) -> None:
        stack_name: str
        with open(EXECUTED_FILE, "r") as f:
            stack_name = f.read().strip()
        stack = cfn_resource.Stack(stack_name)
        self.assertIn(stack.stack_status, ["CREATE_COMPLETE", "UPDATE_COMPLETE"])


class RedactTestCase(TestCase):
    stack_name: str
    stack: Stack

    # noinspection PyMissingOrEmptyDocstring
    @classmethod
    def setUpClass(cls) -> None:
        stack_name: str
        with open(EXECUTED_FILE, "r") as f:
            cls.stack_name = f.read().strip()
        cls.stack = cfn_resource.Stack(cls.stack_name)


class OutputTests(RedactTestCase):
    def test_verify_output_hello_world(self) -> None:
        self.assertIn("HelloWorldOutput", [o["OutputKey"] for o in self.stack.outputs])

    def test_verify_output_test(self) -> None:
        self.assertIn("TestOutput", [o["OutputKey"] for o in self.stack.outputs])


class HelloWorldLogs(RedactTestCase):
    output_name: str = "HelloWorldOutput"
    log_messages: List[str]

    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        output = {o["OutputKey"]: o for o in self.stack.outputs}[self.output_name]
        log_group_name, log_stream_name, aws_request_id = output["OutputValue"].split("|", 2)
        log_output: List[FilterLogEventsResponseTypeDef] = list(
            log_events_paginator.paginate(
                logGroupName=log_group_name,
                logStreamNames=[log_stream_name],
                filterPattern=f'"{aws_request_id}" "Request Body"',
            )
        )
        self.log_messages = []
        for r in log_output:
            for e in r["events"]:
                self.log_messages.append(e["message"])

    def test_number_messages(self):
        self.assertEqual(1, len(self.log_messages))

    def test_redaction(self):
        request = json.loads(self.log_messages[0].split("Request Body: ", 1)[1])
        properties = request["ResourceProperties"]
        del properties["ServiceToken"]
        self.assertEqual(
            properties,
            {
                "Test": "[REDACTED]",
                "DeleteMe": "Unredacted",
                "Unredacted": "Unredacted",
                "Example": "[REDACTED]",
                "DeleteMeExtended": "Unredacted",
                "Custom": "Unredacted",
            },
        )


class TestLogs(RedactTestCase):
    output_name: str = "TestOutput"
    log_messages: List[str]

    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        output = {o["OutputKey"]: o for o in self.stack.outputs}[self.output_name]
        log_group_name, log_stream_name, aws_request_id = output["OutputValue"].split("|", 2)
        log_output: List[FilterLogEventsResponseTypeDef] = list(
            log_events_paginator.paginate(
                logGroupName=log_group_name,
                logStreamNames=[log_stream_name],
                filterPattern=f'"{aws_request_id}" "Request Body"',
            )
        )
        self.log_messages = []
        for r in log_output:
            for e in r["events"]:
                self.log_messages.append(e["message"])

    def test_number_messages(self):
        self.assertEqual(1, len(self.log_messages))

    def test_redaction(self):
        request = json.loads(self.log_messages[0].split("Request Body: ", 1)[1])
        properties = request["ResourceProperties"]
        del properties["ServiceToken"]
        self.assertEqual(
            properties,
            {
                "Test": "[REDACTED]",
                "DeleteMe": "[REDACTED]",
                "Unredacted": "Unredacted",
                "Example": "[REDACTED]",
                "DeleteMeExtended": "[REDACTED]",
                "Custom": "[REDACTED]",
            },
        )


if __name__ == "__main__":
    ut_main()
