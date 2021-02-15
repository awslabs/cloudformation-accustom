# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" Constants for the accustom library.

These are constants are the Custom Resource Request Type Constants
"""


class Status:
    """CloudFormation Custom Resource Status Constants

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    """
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'


class RequestType:
    """CloudFormation Custom Resource Request Type Constants

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requesttypes.html
    """
    CREATE = 'Create'
    UPDATE = 'Update'
    DELETE = 'Delete'


class RedactMode:
    """RedactMode Options"""
    ALLOWLIST = 'allow'
    BLOCKLIST = 'block'

    # DEPRECATED NAMES
    BLACKLIST = 'black'
    WHITELIST = 'white'
