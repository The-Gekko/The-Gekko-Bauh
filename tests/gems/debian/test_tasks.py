import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh import __app_name__
from bauh.gems.debian.tasks import SynchronizePackages


class SynchronizePackagesShouldSynchronizeTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.ts_file = f'{self.tmp_dir.name}/sync_pkgs.ts'

        patcher = patch(f'{__app_name__}.gems.debian.tasks.PACKAGE_SYNC_TIMESTAMP_FILE', self.ts_file)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.logger = Mock()

    def _write_timestamp(self, timestamp):
        with open(self.ts_file, 'w') as f:
            f.write(str(timestamp))

    def test_must_return_true_when_period_is_not_positive(self):
        self._write_timestamp(datetime.now(timezone.utc).timestamp())
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': 0}, self.logger))
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': -1}, self.logger))

    def test_must_return_true_when_period_is_invalid(self):
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': 'abc'}, self.logger))

    def test_must_return_true_when_timestamp_file_is_missing(self):
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': 60}, self.logger))

    def test_must_return_true_when_timestamp_is_invalid(self):
        self._write_timestamp('not-a-number')
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': 60}, self.logger))

    def test_must_return_false_when_last_synchronization_is_recent(self):
        self._write_timestamp((datetime.now(timezone.utc) - timedelta(minutes=59)).timestamp())
        self.assertFalse(SynchronizePackages.should_synchronize({'sync_pkgs.time': 60}, self.logger))

    def test_must_return_true_when_last_synchronization_has_expired(self):
        self._write_timestamp((datetime.now(timezone.utc) - timedelta(minutes=61)).timestamp())
        self.assertTrue(SynchronizePackages.should_synchronize({'sync_pkgs.time': 60}, self.logger))
