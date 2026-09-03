import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bauh import __app_name__, __package_name__
from bauh.migration import LEGACY_APP_NAME, migrate_legacy_user_data


class MigrateLegacyUserDataTest(unittest.TestCase):
    """Migración de ~/.config/bauh y ~/.local/share/bauh al nombre propio del proyecto."""

    def setUp(self):
        self.home = TemporaryDirectory()
        self.addCleanup(self.home.cleanup)

        patcher = patch.object(Path, 'home', staticmethod(lambda: Path(self.home.name)))
        patcher.start()
        self.addCleanup(patcher.stop)

        root_patcher = patch(f'{__package_name__}.migration.user.is_root', return_value=False)
        root_patcher.start()
        self.addCleanup(root_patcher.stop)

    def _legacy_config(self, *, theme: str = 'aurora') -> str:
        path = os.path.join(self.home.name, '.config', LEGACY_APP_NAME)
        os.makedirs(os.path.join(path, 'arch'))

        with open(os.path.join(path, 'config.yml'), 'w') as f:
            f.write(f'ui:\n  theme: {theme}\n')

        with open(os.path.join(path, 'arch', 'updates_ignored.txt'), 'w') as f:
            f.write('linux\n')

        return path

    def _current_config(self) -> str:
        return os.path.join(self.home.name, '.config', __app_name__)

    def test_must_copy_the_legacy_config_when_the_new_one_does_not_exist(self):
        self._legacy_config()

        migrated = migrate_legacy_user_data(__app_name__)

        self.assertEqual([self._current_config()], migrated)
        with open(os.path.join(self._current_config(), 'config.yml')) as f:
            self.assertIn('theme: aurora', f.read())
        self.assertTrue(os.path.isfile(os.path.join(self._current_config(), 'arch', 'updates_ignored.txt')))

    def test_must_leave_the_legacy_directory_untouched(self):
        legacy = self._legacy_config()

        migrate_legacy_user_data(__app_name__)

        # El proyecto original debe seguir arrancando exactamente igual tras la migración.
        self.assertTrue(os.path.isdir(legacy))
        with open(os.path.join(legacy, 'config.yml')) as f:
            self.assertIn('theme: aurora', f.read())

    def test_must_not_overwrite_an_existing_configuration(self):
        self._legacy_config(theme='aurora')
        os.makedirs(self._current_config())

        with open(os.path.join(self._current_config(), 'config.yml'), 'w') as f:
            f.write('ui:\n  theme: light\n')

        self.assertEqual([], migrate_legacy_user_data(__app_name__))

        with open(os.path.join(self._current_config(), 'config.yml')) as f:
            self.assertIn('theme: light', f.read())

    def test_must_migrate_the_shared_data_dir_with_the_user_themes(self):
        legacy_themes = os.path.join(self.home.name, '.local', 'share', LEGACY_APP_NAME, 'themes')
        os.makedirs(legacy_themes)

        with open(os.path.join(legacy_themes, 'mine.qss'), 'w') as f:
            f.write('QWidget {}')

        migrated = migrate_legacy_user_data(__app_name__)

        expected = os.path.join(self.home.name, '.local', 'share', __app_name__)
        self.assertIn(expected, migrated)
        self.assertTrue(os.path.isfile(os.path.join(expected, 'themes', 'mine.qss')))

    def test_must_not_migrate_the_cache(self):
        legacy_cache = os.path.join(self.home.name, '.cache', LEGACY_APP_NAME)
        os.makedirs(legacy_cache)

        migrate_legacy_user_data(__app_name__)

        # La caché se regenera sola y puede ocupar cientos de megabytes.
        self.assertFalse(os.path.exists(os.path.join(self.home.name, '.cache', __app_name__)))

    def test_must_do_nothing_when_there_is_nothing_to_migrate(self):
        self.assertEqual([], migrate_legacy_user_data(__app_name__))

    def test_must_do_nothing_when_the_app_still_uses_the_legacy_name(self):
        self._legacy_config()
        self.assertEqual([], migrate_legacy_user_data(LEGACY_APP_NAME))

    def test_must_do_nothing_when_running_as_root(self):
        self._legacy_config()

        with patch(f'{__package_name__}.migration.user.is_root', return_value=True):
            self.assertEqual([], migrate_legacy_user_data(__app_name__))

        self.assertFalse(os.path.exists(self._current_config()))

    def test_must_not_fail_when_the_copy_is_not_possible(self):
        self._legacy_config()

        with patch(f'{__package_name__}.migration.shutil.copytree', side_effect=OSError('sin espacio')):
            self.assertEqual([], migrate_legacy_user_data(__app_name__))
