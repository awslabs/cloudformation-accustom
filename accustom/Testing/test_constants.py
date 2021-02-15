from accustom import Status
from accustom import RequestType
from accustom import RedactMode

from unittest import TestCase, main as umain


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
        self.assertEqual('black', RedactMode.BLACKLIST)

    def test_whitelist(self):
        self.assertEqual('white', RedactMode.WHITELIST)


if __name__ == '__main__':
    umain()
