# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Testing of the "constant" library
"""
from accustom import Status
from accustom import RequestType
from accustom import RedactMode

from unittest import TestCase, main as ut_main


class StatusTests(TestCase):
    def test_success(self):
        self.assertEqual('SUCCESS', Status.SUCCESS)

    def test_failed(self):
        self.assertEqual('FAILED', Status.FAILED)


class RequestTypeTests(TestCase):
    def test_create(self):
        self.assertEqual('Create', RequestType.CREATE)

    def test_update(self):
        self.assertEqual('Update', RequestType.UPDATE)

    def test_delete(self):
        self.assertEqual('Delete', RequestType.DELETE)


class RedactModeTests(TestCase):
    def test_blocklist(self):
        self.assertEqual('block', RedactMode.BLOCKLIST)

    def test_allowlist(self):
        self.assertEqual('allow', RedactMode.ALLOWLIST)

    def test_blacklist(self):
        self.assertEqual('block', RedactMode.BLACKLIST)

    def test_whitelist(self):
        self.assertEqual('allow', RedactMode.WHITELIST)


if __name__ == '__main__':
    ut_main()
