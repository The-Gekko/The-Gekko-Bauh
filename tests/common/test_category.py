import os
import tempfile
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock

from bauh.commons.category import CategoriesDownloader
from bauh.commons.util import map_timestamp_file


@contextmanager
def local_timezone(posix_tz: str):
    """Cambia temporalmente la zona horaria del proceso (formato POSIX, no requiere tzdata)."""
    previous = os.environ.get('TZ')
    os.environ['TZ'] = posix_tz
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = previous
        time.tzset()


class CategoriesDownloaderShouldDownloadTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.categories_path = f'{self.tmp_dir.name}/categories.txt'
        self.ts_path = map_timestamp_file(self.categories_path)
        self.http_client = Mock()
        self.downloader = self._new_downloader(expiration=24)

    def _new_downloader(self, expiration) -> CategoriesDownloader:
        return CategoriesDownloader(id_='test', http_client=self.http_client, logger=Mock(), manager=Mock(),
                                    url_categories_file='https://localhost/categories.txt',
                                    categories_path=self.categories_path, internet_checker=Mock(),
                                    expiration=expiration, internet_connection=True)

    def _write_cache(self, timestamp: float, content: str = 'app=cat1,cat2'):
        with open(self.categories_path, 'w') as f:
            f.write(content)

        with open(self.ts_path, 'w') as f:
            f.write(str(timestamp))

    def test_should_download__must_return_true_when_no_expiration_is_set(self):
        self._write_cache(datetime.now(timezone.utc).timestamp())
        self.assertTrue(self._new_downloader(expiration=None).should_download())
        self.assertTrue(self._new_downloader(expiration=0).should_download())

    def test_should_download__must_return_true_when_cached_files_are_missing(self):
        self.assertTrue(self.downloader.should_download())

        with open(self.categories_path, 'w') as f:
            f.write('app=cat1')

        self.assertTrue(self.downloader.should_download())

    def test_should_download__must_return_true_when_timestamp_is_invalid(self):
        self._write_cache(0)

        with open(self.ts_path, 'w') as f:
            f.write('not-a-number')

        self.assertTrue(self.downloader.should_download())

    def test_should_download__must_return_false_when_cache_is_recent(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=23)).timestamp())
        self.assertFalse(self.downloader.should_download())

    def test_should_download__must_return_true_when_cache_has_expired(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=25)).timestamp())
        self.assertTrue(self.downloader.should_download())

    @unittest.skipUnless(hasattr(time, 'tzset'), 'time.tzset no disponible')
    def test_should_download__must_not_depend_on_the_local_timezone(self):
        # 'WST3' = UTC-3 y 'EST-9' = UTC+9 en notación POSIX
        for tz in ('WST3', 'EST-9', 'UTC0'):
            with local_timezone(tz):
                self._write_cache((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
                self.assertFalse(self.downloader.should_download(), tz)

                self._write_cache((datetime.now(timezone.utc) - timedelta(hours=24, minutes=1)).timestamp())
                self.assertTrue(self.downloader.should_download(), tz)

    @unittest.skipUnless(hasattr(time, 'tzset'), 'time.tzset no disponible')
    def test_download_categories__must_cache_a_real_utc_epoch_timestamp(self):
        response = Mock()
        response.text = 'firefox=network,web\ngimp=graphics'
        self.http_client.get.return_value = response

        with local_timezone('EST-9'):
            categories = self.downloader.download_categories()

            with open(self.ts_path) as f:
                cached_timestamp = float(f.read())

            # el timestamp guardado no debe estar desplazado por la zona horaria local
            self.assertAlmostEqual(datetime.now(timezone.utc).timestamp(), cached_timestamp, delta=60)
            self.assertFalse(self.downloader.should_download())

        self.assertEqual({'firefox': ['network', 'web'], 'gimp': ['graphics']}, categories)
