import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock

from bauh.gems.debian import URL_BAUH_FILES, URL_SUGGESTIONS_FILE
from bauh.gems.debian.suggestions import DebianSuggestionsDownloader


class DebianSuggestionsDownloaderTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.suggestions_file = f'{self.tmp_dir.name}/suggestions.txt'
        self.ts_file = f'{self.suggestions_file}.ts'

        # las rutas se cachean a nivel de clase: se apuntan al directorio temporal y se restauran al final
        DebianSuggestionsDownloader._file_suggestions = self.suggestions_file
        DebianSuggestionsDownloader._file_suggestions_ts = self.ts_file
        self.addCleanup(setattr, DebianSuggestionsDownloader, '_file_suggestions', None)
        self.addCleanup(setattr, DebianSuggestionsDownloader, '_file_suggestions_ts', None)

        self.downloader = DebianSuggestionsDownloader(logger=Mock(), http_client=Mock(), i18n={}, file_url=None)
        self.config = {'suggestions.exp': 24}

    def _write_cache(self, timestamp, content: str = '5=firefox'):
        with open(self.suggestions_file, 'w') as f:
            f.write(content)

        with open(self.ts_file, 'w') as f:
            f.write(str(timestamp))

    def test_default_url__must_point_to_the_centralized_files_host(self):
        self.assertEqual(URL_SUGGESTIONS_FILE, self.downloader._file_url)
        self.assertTrue(URL_SUGGESTIONS_FILE.startswith(URL_BAUH_FILES))

    def test_should_download__must_return_true_when_cache_files_are_missing(self):
        self.assertTrue(self.downloader.should_download(self.config))

        with open(self.suggestions_file, 'w') as f:
            f.write('5=firefox')

        # solo falta el fichero de timestamp: debe volver a descargarse sin lanzar excepciones
        self.assertTrue(self.downloader.should_download(self.config))

    def test_should_download__must_return_true_when_expiration_is_disabled(self):
        self._write_cache(datetime.now(timezone.utc).timestamp())
        self.assertTrue(self.downloader.should_download({'suggestions.exp': 0}))
        self.assertFalse(self.downloader.should_download({'suggestions.exp': 0}, only_positive_exp=True))

    def test_should_download__must_return_false_when_cache_is_recent(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=23)).timestamp())
        self.assertFalse(self.downloader.should_download(self.config))

    def test_should_download__must_return_true_when_cache_has_expired(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=25)).timestamp())
        self.assertTrue(self.downloader.should_download(self.config))

    def test_should_download__must_return_true_when_timestamp_is_invalid(self):
        self._write_cache('not-a-number')
        self.assertTrue(self.downloader.should_download(self.config))

    def test_should_download__must_return_false_when_a_local_file_is_mapped(self):
        downloader = DebianSuggestionsDownloader(logger=Mock(), http_client=Mock(), i18n={},
                                                 file_url='/tmp/suggestions.txt')
        self.assertFalse(downloader.should_download(self.config))
