# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Exceptions for the accustom library.

These are the exceptions that can be returned by accustom
"""


class CannotApplyRuleToStandaloneRedactionConfig(Exception):
    """Indicates that a second rule set was attempted to be applied to a standalone"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class ConflictingValue(Exception):
    """Indicates that there is already a record with this value"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class NoPhysicalResourceIdException(Exception):
    """Indicates that there was no valid value to use for PhysicalResourceId"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class InvalidResponseStatusException(Exception):
    """Indicates that there response code was not SUCCESS or FAILED"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class DataIsNotDictException(Exception):
    """Indicates that a Dictionary was not passed as Data"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class FailedToSendResponseException(Exception):
    """Indicates there was a problem sending the response"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class NotValidRequestObjectException(Exception):
    """Indicates that the event passed in is not a valid Request Object"""

    def __init__(self, *args):
        Exception.__init__(self, *args)


class ResponseTooLongException(Exception):
    """Indicates that the produced response exceeds 4096 bytes and thus is too long"""

    def __init__(self, *args):
        Exception.__init__(self, *args)
