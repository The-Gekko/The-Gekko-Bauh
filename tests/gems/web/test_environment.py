import io
import os
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh import __app_name__
from bauh.gems.web.environment import (
    EnvironmentUpdater,
    extract_tar_safely,
    validate_tar_members,
)


def build_tar(path: str, members) -> None:
    """
    Genera un tar.gz con los miembros indicados: tuplas (nombre, tipo, contenido_o_destino_del_enlace)
    donde tipo es 'file', 'dir', 'sym', 'lnk' o 'chr'.
    """
    with tarfile.open(path, 'w:gz') as tf:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)

            if kind == 'file':
                data = (payload or '').encode()
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            else:
                info.type = {'dir': tarfile.DIRTYPE, 'sym': tarfile.SYMTYPE, 'lnk': tarfile.LNKTYPE,
                             'chr': tarfile.CHRTYPE}[kind]

                if kind in ('sym', 'lnk'):
                    info.linkname = payload

                tf.addfile(info)


class SafeTarExtractionTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.tar_path = f'{self.tmp_dir.name}/archive.tar.gz'
        self.dest = f'{self.tmp_dir.name}/dest'
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

    def test_must_extract_a_regular_archive_with_relative_symlinks(self):
        build_tar(self.tar_path, [('node-v1', 'dir', None),
                                  ('node-v1/bin', 'dir', None),
                                  ('node-v1/bin/node', 'file', 'binary'),
                                  ('node-v1/lib/npm-cli.js', 'file', 'js'),
                                  ('node-v1/bin/npm', 'sym', '../lib/npm-cli.js')])

        with tarfile.open(self.tar_path) as tf:
            validate_tar_members(tf, self.dest)
            extract_tar_safely(tf, self.dest)

        self.assertTrue(os.path.isfile(f'{self.dest}/node-v1/bin/node'))
        self.assertTrue(os.path.islink(f'{self.dest}/node-v1/bin/npm'))

        with open(f'{self.dest}/node-v1/bin/npm') as f:
            self.assertEqual('js', f.read())

    def test_must_reject_members_escaping_the_destination_with_parent_references(self):
        self._assert_rejected([('safe.txt', 'file', 'ok'), ('../evil.txt', 'file', 'evil')])
        self.assertFalse(os.path.exists(f'{self.tmp_dir.name}/evil.txt'))

    def test_must_reject_members_with_absolute_paths(self):
        outside = f'{self.tmp_dir.name}/absolute.txt'
        self._assert_rejected([(outside, 'file', 'evil')], must_raise_on_extract=False)
        self.assertFalse(os.path.exists(outside))

    def test_must_reject_symlinks_pointing_outside_the_destination(self):
        self._assert_rejected([('link', 'sym', '../../outside')])
        self._assert_rejected([('link', 'sym', '/etc/passwd')])
        self._assert_rejected([('dir/link', 'sym', '../../outside')])

    def test_must_reject_hard_links_pointing_outside_the_destination(self):
        self._assert_rejected([('link', 'lnk', '../outside')])
        self._assert_rejected([('link', 'lnk', '/etc/passwd')])

    def test_must_reject_special_files(self):
        self._assert_rejected([('device', 'chr', None)])


class EnvironmentUpdaterShouldDownloadSettingsTest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.settings_file = f'{self.tmp_dir.name}/environment.yml'
        self.ts_file = f'{self.tmp_dir.name}/environment.ts'

        for name, value in (('ENVIRONMENT_SETTINGS_CACHED_FILE', self.settings_file),
                            ('ENVIRONMENT_SETTINGS_TS_FILE', self.ts_file)):
            patcher = patch(f'{__app_name__}.gems.web.environment.{name}', value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.updater = EnvironmentUpdater(logger=Mock(), http_client=Mock(), file_downloader=Mock(), i18n={})
        self.config = {'environment': {'cache_exp': 24}}

    def _write_cache(self, timestamp):
        with open(self.settings_file, 'w') as f:
            f.write('nodejs:\n  version: 1\n')

        with open(self.ts_file, 'w') as f:
            f.write(str(timestamp))

    def test_must_return_true_when_expiration_is_disabled(self):
        self._write_cache(datetime.now(timezone.utc).timestamp())
        self.assertTrue(self.updater.should_download_settings({'environment': {'cache_exp': 0}}))

    def test_must_return_true_when_cache_files_are_missing(self):
        self.assertTrue(self.updater.should_download_settings(self.config))

    def test_must_return_false_when_cache_is_recent(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=23)).timestamp())
        self.assertFalse(self.updater.should_download_settings(self.config))

    def test_must_return_true_when_cache_has_expired(self):
        self._write_cache((datetime.now(timezone.utc) - timedelta(hours=25)).timestamp())
        self.assertTrue(self.updater.should_download_settings(self.config))

    def test_must_return_true_when_timestamp_is_invalid(self):
        self._write_cache('not-a-number')
        self.assertTrue(self.updater.should_download_settings(self.config))
