# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" Exceptions for the accustom library.

These are the exceptions that can be returned by accustom
"""


class CannotApplyRuleToStandaloneRedactionConfig(Exception):
    """Indicates that a second rule set was attempted to be applied to a standalone"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ConflictingValue(Exception):
    """Indicates that there is already a record with this value"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NoPhysicalResourceIdException(Exception):
    """Indicates that there was no valid value to use for PhysicalResourceId"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class InvalidResponseStatusException(Exception):
    """Indicates that there response code was not SUCCESS or FAILED"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class DataIsNotDictException(Exception):
    """Indicates that a Dictionary was not passed as Data"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class FailedToSendResponseException(Exception):
    """Indicates there was a problem sending the response"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotValidRequestObjectException(Exception):
    """Indicates that the event passed in is not a valid Request Object"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
