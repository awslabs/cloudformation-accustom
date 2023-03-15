# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Lambda Code for testng Redaction Functionality
"""
import logging

from accustom import RedactionConfig, RedactionRuleSet, ResponseObject, decorator

logging.getLogger().setLevel(logging.DEBUG)

ruleSetDefault = RedactionRuleSet()
ruleSetDefault.add_property_regex("^Test$")
ruleSetDefault.add_property("Example")

ruleSetCustom = RedactionRuleSet("^Custom::Test$")
ruleSetCustom.add_property("Custom")
ruleSetCustom.add_property_regex("^DeleteMe.*$")

rc = RedactionConfig(redactResponseURL=True)
rc.add_rule_set(ruleSetDefault)
rc.add_rule_set(ruleSetCustom)

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
@decorator(hideResourceDeleteFailure=True, redactConfig=rc)
def handler(event, context) -> ResponseObject:
    """
    Stub handler function for this Lambda Function

    :param event: Event Input
    :param context: Lambda Context
    :return: A ResponseObject containing the log location
    """
    # Passing the context event information back to the function
    return ResponseObject(
        data={
            "log_group_name": context.log_group_name,
            "log_stream_name": context.log_stream_name,
            "aws_request_id": context.aws_request_id,
        }
    )
