# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Lambda Code for Testing Timeout and Chaining Functionality
"""

import logging
from time import sleep

from accustom import sdecorator as sdecorator

logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
@sdecorator(hideResourceDeleteFailure=True, decoratorHandleDelete=True, expectedProperties=["TestProperty"])
def handler(event, context) -> None:
    """
    Stab handler for this Lambda Function

    :param event: Event Input
    :param context: Lambda Context
    :return: Nothing
    """
    logger.info("Sleeping for 30 seconds")
    sleep(30)
