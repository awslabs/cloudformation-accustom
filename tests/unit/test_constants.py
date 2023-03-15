# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Testing of the "constant" library
"""
from unittest import TestCase
from unittest import main as ut_main

from accustom import RedactMode, RequestType, Status


class StatusTests(TestCase):
    def test_success(self) -> None:
        self.assertEqual("SUCCESS", Status.SUCCESS)

    def test_failed(self) -> None:
        self.assertEqual("FAILED", Status.FAILED)


class RequestTypeTests(TestCase):
    def test_create(self) -> None:
        self.assertEqual("Create", RequestType.CREATE)

    def test_update(self) -> None:
        self.assertEqual("Update", RequestType.UPDATE)

    def test_delete(self) -> None:
        self.assertEqual("Delete", RequestType.DELETE)


class RedactModeTests(TestCase):
    def test_blocklist(self) -> None:
        self.assertEqual("block", RedactMode.BLOCKLIST)

    def test_allowlist(self) -> None:
        self.assertEqual("allow", RedactMode.ALLOWLIST)

    def test_blacklist(self) -> None:
        self.assertEqual("black", RedactMode.BLACKLIST)

    def test_whitelist(self) -> None:
        self.assertEqual("white", RedactMode.WHITELIST)


if __name__ == "__main__":
    ut_main()
