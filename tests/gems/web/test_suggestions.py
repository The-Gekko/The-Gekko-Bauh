import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock

from bauh.gems.web import URL_BAUH_FILES, URL_SUGGESTIONS_FILE
from bauh.gems.web.suggestions import SuggestionsManager


class SuggestionsManagerShouldDownloadTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.manager = SuggestionsManager(http_client=Mock(), logger=Mock(), i18n={}, file_url=None)
        self.manager._cached_file_path = f'{self.tmp_dir.name}/suggestions.yml'
        self.manager._cached_file_ts_path = f'{self.tmp_dir.name}/suggestions.ts'
        self.config = {'suggestions': {'cache_exp': 1}}  # días

    def _write_cache(self, timestamp):
        with open(self.manager._cached_file_path, 'w') as f:
            f.write('firefox:\n  url: https://firefox.com\n')

        with open(self.manager._cached_file_ts_path, 'w') as f:
            f.write(str(timestamp))

    def test_default_url__must_point_to_the_centralized_files_host(self):
        self.assertEqual(URL_SUGGESTIONS_FILE, self.manager.file_url)
        self.assertTrue(URL_SUGGESTIONS_FILE.startswith(URL_BAUH_FILES))

    def test_must_return_true_when_no_expiration_is_defined(self):
        self._write_cache(datetime.now(timezone.utc).timestamp())
        self.assertTrue(self.manager.should_download({'suggestions': {'cache_exp': None}}))
        self.assertTrue(self.manager.should_download({'suggestions': {'cache_exp': 0}}))

    def test_must_return_true_when_cache_files_are_missing(self):
        self.assertTrue(self.manager.should_download(self.config))

    def test_must_return_false_when_cache_is_recent(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=23)).timestamp())
        self.assertFalse(self.manager.should_download(self.config))

    def test_must_return_true_when_cache_has_expired(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(days=1, minutes=1)).timestamp())
        self.assertTrue(self.manager.should_download(self.config))

    def test_must_return_true_when_timestamp_is_invalid(self):
        self._write_cache('not-a-number')
        self.assertTrue(self.manager.should_download(self.config))

    def test_must_return_false_when_a_local_file_is_mapped(self):
        manager = SuggestionsManager(http_client=Mock(), logger=Mock(), i18n={}, file_url='/tmp/suggestions.yml')
        self.assertFalse(manager.should_download(self.config))
