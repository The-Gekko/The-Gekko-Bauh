import io
import os
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh import __package_name__
from bauh.gems.appimage import (
    URL_BAUH_FILES,
    URL_COMPRESSED_DATABASES,
    URL_SUGGESTIONS_FILE,
)
from bauh.gems.appimage.worker import (
    AppImageSuggestionsDownloader,
    DatabaseUpdater,
    extract_tar_safely,
    validate_tar_members,
)


def build_tar(path: str, members) -> None:
    """Genera un tar.gz con tuplas (nombre, tipo, contenido_o_destino) donde tipo es 'file', 'dir', 'sym' o 'lnk'."""
    with tarfile.open(path, 'w:gz') as tf:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)

            if kind == 'file':
                data = (payload or '').encode()
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            else:
                info.type = {'dir': tarfile.DIRTYPE, 'sym': tarfile.SYMTYPE, 'lnk': tarfile.LNKTYPE}[kind]

                if kind in ('sym', 'lnk'):
                    info.linkname = payload

                tf.addfile(info)


class SafeTarExtractionTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.tar_path = f'{self.tmp_dir.name}/dbs.tar.gz'
        self.dest = f'{self.tmp_dir.name}/appimage'
        os.mkdir(self.dest)

    def _assert_rejected(self, members, must_raise_on_extract: bool = True):
        """
        La validación manual (Python < 3.12) debe rechazar siempre el miembro. La extracción con el filtro 'data'
        (Python >= 3.12) rechaza los miembros peligrosos salvo las rutas absolutas, que neutraliza recortando la '/'
        inicial: en ese caso solo se exige que no se escriba nada fuera del destino.
        """
        build_tar(self.tar_path, members)

        with tarfile.open(self.tar_path) as tf, self.assertRaises(tarfile.TarError):
            validate_tar_members(tf, self.dest)

        with tarfile.open(self.tar_path) as tf:
            if must_raise_on_extract:
                with self.assertRaises(tarfile.TarError):
                    extract_tar_safely(tf, self.dest)
            else:
                try:
                    extract_tar_safely(tf, self.dest)
                except tarfile.TarError:
                    pass

    def _read(self, path: str) -> str:
        with open(path) as f:
            return f.read()

    def test_must_extract_database_files(self):
        build_tar(self.tar_path, [('apps.db', 'file', 'apps'), ('releases.db', 'file', 'releases')])

        with tarfile.open(self.tar_path) as tf:
            validate_tar_members(tf, self.dest)
            extract_tar_safely(tf, self.dest)

        self.assertEqual('apps', self._read(f'{self.dest}/apps.db'))
        self.assertEqual('releases', self._read(f'{self.dest}/releases.db'))

    def test_must_reject_members_escaping_the_destination(self):
        self._assert_rejected([('apps.db', 'file', 'apps'), ('../evil.db', 'file', 'evil')])
        self.assertFalse(os.path.exists(f'{self.tmp_dir.name}/evil.db'))

        outside = f'{self.tmp_dir.name}/absolute.db'
        self._assert_rejected([(outside, 'file', 'evil')], must_raise_on_extract=False)
        self.assertFalse(os.path.exists(outside))

    def test_must_reject_links_pointing_outside_the_destination(self):
        self._assert_rejected([('link.db', 'sym', '../../outside')])
        self._assert_rejected([('link.db', 'sym', '/etc/passwd')])
        self._assert_rejected([('link.db', 'lnk', '../outside')])


class DatabaseUpdaterShouldUpdateTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.cache_dir = self.tmp_dir.name
        self.ts_file = f'{self.cache_dir}/dbs.ts'
        self.apps_db = f'{self.cache_dir}/apps.db'
        self.releases_db = f'{self.cache_dir}/releases.db'

        for name, value in (('APPIMAGE_CACHE_DIR', self.cache_dir), ('DATABASES_TS_FILE', self.ts_file),
                            ('DATABASE_APPS_FILE', self.apps_db), ('DATABASE_RELEASES_FILE', self.releases_db)):
            patcher = patch(f'{__package_name__}.gems.appimage.worker.{name}', value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.updater = DatabaseUpdater(i18n={'appimage.task.db_update': 'db'}, http_client=Mock(), logger=Mock(),
                                       taskman=Mock())
        self.config = {'database': {'expiration': 60}}  # minutos

    def _write_databases(self, timestamp):
        for db in (self.apps_db, self.releases_db):
            with open(db, 'w') as f:
                f.write('db')

        with open(self.ts_file, 'w') as f:
            f.write(str(timestamp))

    def test_database_url__must_point_to_the_centralized_files_host(self):
        self.assertTrue(URL_COMPRESSED_DATABASES.startswith(URL_BAUH_FILES))
        self.assertTrue(URL_COMPRESSED_DATABASES.endswith('/appimage/dbs.tar.gz'))

    def test_must_return_true_when_expiration_is_disabled(self):
        self._write_databases(datetime.now(timezone.utc).timestamp())
        self.assertTrue(self.updater.should_update({'database': {'expiration': 0}}))

    def test_must_return_true_when_database_files_are_missing(self):
        self.assertTrue(self.updater.should_update(self.config))

        with open(self.ts_file, 'w') as f:
            f.write(str(datetime.now(timezone.utc).timestamp()))

        self.assertTrue(self.updater.should_update(self.config))

    def test_must_return_false_when_databases_are_recent(self):
        self._write_databases((datetime.now(timezone.utc) - timedelta(minutes=59)).timestamp())
        self.assertFalse(self.updater.should_update(self.config))

    def test_must_return_true_when_databases_have_expired(self):
        self._write_databases((datetime.now(timezone.utc) - timedelta(minutes=61)).timestamp())
        self.assertTrue(self.updater.should_update(self.config))

    def test_must_return_true_when_timestamp_is_invalid(self):
        self._write_databases('not-a-number')
        self.assertTrue(self.updater.should_update(self.config))


class AppImageSuggestionsDownloaderShouldDownloadTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.downloader = AppImageSuggestionsDownloader(logger=Mock(), http_client=Mock(), i18n={}, file_url=None)
        self.downloader._cached_file_path = f'{self.tmp_dir.name}/suggestions.txt'
        self.downloader._cached_ts_file_path = f'{self.tmp_dir.name}/suggestions.ts'
        self.config = {'suggestions': {'expiration': 24}}  # horas

    def _write_cache(self, timestamp):
        with open(self.downloader.cached_file_path, 'w') as f:
            f.write('5=firefox')

        with open(self.downloader.cached_ts_file_path, 'w') as f:
            f.write(str(timestamp))

    def test_default_url__must_point_to_the_centralized_files_host(self):
        self.assertEqual(URL_SUGGESTIONS_FILE, self.downloader._file_url)
        self.assertTrue(URL_SUGGESTIONS_FILE.startswith(URL_BAUH_FILES))

    def test_must_return_true_when_cache_files_are_missing(self):
        self.assertTrue(self.downloader.should_download(self.config))

    def test_must_return_false_when_cache_is_recent(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=23)).timestamp())
        self.assertFalse(self.downloader.should_download(self.config))

    def test_must_return_true_when_cache_has_expired(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=25)).timestamp())
        self.assertTrue(self.downloader.should_download(self.config))

    def test_must_return_false_when_a_local_file_is_mapped(self):
        downloader = AppImageSuggestionsDownloader(logger=Mock(), http_client=Mock(), i18n={},
                                                   file_url='/tmp/suggestions.txt')
        self.assertFalse(downloader.should_download(self.config))
