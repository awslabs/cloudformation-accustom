# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Testing of "redaction" library
"""
import logging
from typing import Any, Dict
from unittest import TestCase
from unittest import main as ut_main

from accustom import RedactionConfig, RedactionRuleSet, RedactMode, StandaloneRedactionConfig
from accustom.Exceptions import CannotApplyRuleToStandaloneRedactionConfig

REDACTED_STRING = "[REDACTED]"
NOT_REDACTED_STRING = "NotRedacted"


class RedactionRuleSetTests(TestCase):
    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        self.ruleSet = RedactionRuleSet()

    def test_init(self) -> None:
        # This test ignores the setUp resources
        rs = RedactionRuleSet("^Custom::Test$")
        self.assertEqual("^Custom::Test$", rs.resourceRegex)

    def test_invalid_init(self) -> None:
        # This test ignores the setUp Resources
        with self.assertRaises(TypeError):
            RedactionRuleSet(0)  # type: ignore

    def test_default_regex(self) -> None:
        self.assertEqual("^.*$", self.ruleSet.resourceRegex)

    def test_adding_regex(self) -> None:
        self.ruleSet.add_property_regex("^Test$")
        self.assertIn("^Test$", self.ruleSet._properties)

    def test_adding_invalid_regex(self) -> None:
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            self.ruleSet.add_property_regex(0)  # type: ignore

    def test_adding_property(self) -> None:
        self.ruleSet.add_property("Test")
        self.assertIn("^Test$", self.ruleSet._properties)

    def test_adding_invalid_property(self) -> None:
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            self.ruleSet.add_property(0)  # type: ignore


# noinspection DuplicatedCode,PyUnusedLocal
class RedactionConfigTests(TestCase):
    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        self.ruleSetDefault = RedactionRuleSet()
        self.ruleSetDefault.add_property_regex("^Test$")
        self.ruleSetDefault.add_property("Example")

        self.ruleSetCustom = RedactionRuleSet("^Custom::Test$")
        self.ruleSetCustom.add_property("Custom")
        self.ruleSetCustom.add_property_regex("^DeleteMe.*$")

    def test_defaults(self) -> None:
        rc = RedactionConfig()
        self.assertEqual(rc.redactMode, RedactMode.BLOCKLIST)
        self.assertFalse(rc.redactResponseURL)

    def test_input_values(self) -> None:
        rc = RedactionConfig(redactMode=RedactMode.ALLOWLIST, redactResponseURL=True)
        self.assertEqual(rc.redactMode, RedactMode.ALLOWLIST)
        self.assertTrue(rc.redactResponseURL)

    def test_whitelist_deprecated(self) -> None:
        with self.assertLogs(level=logging.WARNING) as captured:
            rc = RedactionConfig(redactMode=RedactMode.WHITELIST)  # noqa: F841

        self.assertEqual(1, len(captured.records))
        self.assertEqual(
            "The usage of RedactMode.WHITELIST is deprecated, please change to use RedactMode.ALLOWLIST",
            captured.records[0].getMessage(),
        )

    def test_blacklist_deprecated(self) -> None:
        with self.assertLogs(level=logging.WARNING) as captured:
            rc = RedactionConfig(redactMode=RedactMode.BLACKLIST)  # noqa: F841

        self.assertEqual(1, len(captured.records), 1)
        self.assertEqual(
            "The usage of RedactMode.BLACKLIST is deprecated, please change to use RedactMode.BLOCKLIST",
            captured.records[0].getMessage(),
        )

    def test_invalid_input_values(self) -> None:
        with self.assertRaises(TypeError):
            RedactionConfig(redactMode="somestring")  # type: ignore
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            RedactionConfig(redactMode=0)  # type: ignore
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            RedactionConfig(redactResponseURL=0)  # type: ignore

    def test_structure(self) -> None:
        rc = RedactionConfig()
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)

        self.assertIn("^.*$", rc._redactProperties)
        self.assertIn("^Custom::Test$", rc._redactProperties)
        self.assertIn("^Test$", rc._redactProperties["^.*$"])
        self.assertIn("^Example$", rc._redactProperties["^.*$"])
        self.assertIn("^DeleteMe.*$", rc._redactProperties["^Custom::Test$"])
        self.assertIn("^Custom$", rc._redactProperties["^Custom::Test$"])

    def test_redactResponseURL(self) -> None:
        rc = RedactionConfig(redactResponseURL=True)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Test",
        }
        revent = rc._redact(event)  # type: ignore

        self.assertIn("ResponseURL", event)
        self.assertNotIn("ResponseURL", revent)

    def test_blocklist1(self) -> None:
        rc = RedactionConfig()
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Test",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_blocklist2(self) -> None:
        rc = RedactionConfig()
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_allowlist1(self) -> None:
        rc = RedactionConfig(redactMode=RedactMode.ALLOWLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Test",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_allowlist2(self) -> None:
        rc = RedactionConfig(redactMode=RedactMode.ALLOWLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_oldproperties1(self) -> None:
        rc = RedactionConfig()
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Update",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "PhysicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
            "OldResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Test"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Example"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DoNotDelete"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["DoNotDelete"])

    def test_oldproperties2(self) -> None:
        rc = RedactionConfig(redactMode=RedactMode.ALLOWLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event: Dict[str, Any] = {
            "RequestType": "Update",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "PhysicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
            "OldResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DoNotDelete"])


# noinspection DuplicatedCode,PyUnusedLocal
class StandaloneRedactionConfigTests(TestCase):
    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        self.ruleSetDefault = RedactionRuleSet()
        self.ruleSetDefault.add_property_regex("^Test$")
        self.ruleSetDefault.add_property("Example")

        self.ruleSetCustom = RedactionRuleSet("^Custom::Test$")
        self.ruleSetCustom.add_property("Custom")
        self.ruleSetCustom.add_property_regex("^DeleteMe.*$")

    def test_defaults(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault)
        self.assertEqual(RedactMode.BLOCKLIST, rc.redactMode)
        self.assertFalse(rc.redactResponseURL)

    def test_input_values(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.ALLOWLIST, redactResponseURL=True)
        self.assertEqual(RedactMode.ALLOWLIST, rc.redactMode)
        self.assertTrue(rc.redactResponseURL)

    def test_whitelist_deprecated(self) -> None:
        with self.assertLogs(level=logging.WARNING) as captured:
            rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.WHITELIST)  # noqa: F841

        self.assertEqual(1, len(captured.records))
        self.assertEqual(
            "The usage of RedactMode.WHITELIST is deprecated, please change to use RedactMode.ALLOWLIST",
            captured.records[0].getMessage(),
        )

    def test_blacklist_deprecated(self) -> None:
        with self.assertLogs(level=logging.WARNING) as captured:
            rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.BLACKLIST)  # noqa: F841

        self.assertEqual(1, len(captured.records), 1)
        self.assertEqual(
            "The usage of RedactMode.BLACKLIST is deprecated, please change to use RedactMode.BLOCKLIST",
            captured.records[0].getMessage(),
        )

    def test_invalid_input_values(self) -> None:
        with self.assertRaises(TypeError):
            StandaloneRedactionConfig(self.ruleSetDefault, redactMode="somestring")  # type: ignore
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            StandaloneRedactionConfig(self.ruleSetDefault, redactMode=0)  # type: ignore
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            StandaloneRedactionConfig(self.ruleSetDefault, redactResponseURL=0)  # type: ignore
        with self.assertRaises(CannotApplyRuleToStandaloneRedactionConfig):
            rc = StandaloneRedactionConfig(self.ruleSetDefault)
            rc.add_rule_set(self.ruleSetCustom)

    def test_structure(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault)

        self.assertIn("^.*$", rc._redactProperties)
        self.assertIn("^Test$", rc._redactProperties["^.*$"])
        self.assertIn("^Example$", rc._redactProperties["^.*$"])

    def test_redactResponseURL(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactResponseURL=True)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Test",
        }
        revent = rc._redact(event)  # type: ignore

        self.assertIn("ResponseURL", event)
        self.assertNotIn("ResponseURL", revent)

    def test_blocklist(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Test",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_allowlist(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.ALLOWLIST)
        event: Dict[str, Any] = {
            "RequestType": "Create",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

    def test_oldproperties(self) -> None:
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.ALLOWLIST)
        event: Dict[str, Any] = {
            "RequestType": "Update",
            "RequestId": "abcded",
            "ResponseURL": "https://localhost",
            "StackId": "arn:...",
            "LogicalResourceId": "Test",
            "PhysicalResourceId": "Test",
            "ResourceType": "Custom::Hello",
            "ResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
            "OldResourceProperties": {
                "Test": NOT_REDACTED_STRING,
                "Example": NOT_REDACTED_STRING,
                "Custom": NOT_REDACTED_STRING,
                "DeleteMe1": NOT_REDACTED_STRING,
                "DeleteMe2": NOT_REDACTED_STRING,
                "DoNotDelete": NOT_REDACTED_STRING,
            },
        }
        revent = rc._redact(event)  # type: ignore

        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["ResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["ResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["ResourceProperties"]["DoNotDelete"])

        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["Test"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, revent["OldResourceProperties"]["Example"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["Custom"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["Custom"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe1"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DeleteMe2"])
        self.assertEqual(NOT_REDACTED_STRING, event["OldResourceProperties"]["DoNotDelete"])
        self.assertEqual(REDACTED_STRING, revent["OldResourceProperties"]["DoNotDelete"])


if __name__ == "__main__":
    ut_main()
