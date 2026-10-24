import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from bauh.view.core import web_legacy


class WebLegacyTest(TestCase):
    """Restos de la gem Web retirada: se encuentran, se avisa de ellos y se borran a petición."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = self._tmp.name
        self.dirs = {name: os.path.join(tmp, name) for name in ('share', 'cache', 'config', 'apps', 'autostart')}

        for path in self.dirs.values():
            os.makedirs(path)

        web_dir = os.path.join(self.dirs['share'], 'web')
        patches = {
            'WEB_DIR': web_dir,
            'INSTALLED_DIR': os.path.join(web_dir, 'installed'),
            'WEB_CACHE_DIR': os.path.join(self.dirs['cache'], 'web'),
            'WEB_CONFIG_FILE': os.path.join(self.dirs['config'], 'web.yml'),
            'DESKTOP_ENTRIES_DIR': self.dirs['apps'],
            'AUTOSTART_DIR': self.dirs['autostart'],
        }

        for attr, value in patches.items():
            p = patch.object(web_legacy, attr, value)
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write('x')

    def _install_app(self, name: str, autostart: bool = False):
        self._touch(os.path.join(web_legacy.INSTALLED_DIR, name, 'app'))
        self._touch(os.path.join(self.dirs['apps'], f'bauh.web.{name}.desktop'))

        if autostart:
            self._touch(os.path.join(self.dirs['autostart'], f'bauh.web.{name}.desktop'))

    def test_nothing_left_means_no_warning(self):
        self._touch(os.path.join(self.dirs['apps'], 'firefox.desktop'))  # una entrada ajena

        self.assertEqual([], web_legacy.installed_apps())
        self.assertEqual([], web_legacy.leftovers())
        self.assertIsNone(web_legacy.warning(MagicMock()))

    def test_installed_apps_are_found_by_folder_and_by_menu_entry(self):
        self._install_app('whatsapp')
        self._touch(os.path.join(self.dirs['apps'], 'bauh.web.telegram.desktop'))  # solo la entrada

        self.assertEqual(['telegram', 'whatsapp'], web_legacy.installed_apps())

    def test_the_warning_names_the_apps_and_the_command(self):
        self._install_app('whatsapp')
        i18n = {'web_legacy.warning': 'apps={apps} cmd={command}'}

        self.assertEqual('apps=whatsapp cmd=gekko-bauh-cli clean-web-apps', web_legacy.warning(i18n))

    def test_remove_deletes_every_leftover_and_nothing_else(self):
        self._install_app('whatsapp', autostart=True)
        self._touch(os.path.join(web_legacy.WEB_DIR, 'env', 'node', 'bin', 'node'))
        self._touch(os.path.join(web_legacy.WEB_CACHE_DIR, 'index.yml'))
        self._touch(web_legacy.WEB_CONFIG_FILE)
        ajena = os.path.join(self.dirs['apps'], 'firefox.desktop')
        self._touch(ajena)

        self.assertEqual([], web_legacy.remove())

        self.assertEqual([], web_legacy.leftovers())
        self.assertTrue(os.path.exists(ajena))


class CleanWebAppsCommandTest(TestCase):

    def test_without_leftovers_it_says_so(self):
        from bauh.cli import app

        with patch.object(web_legacy, 'leftovers', return_value=[]), patch('builtins.print') as out:
            self.assertEqual(0, app.clean_web_apps(assume_yes=False))

        self.assertIn('No web apps', out.call_args_list[-1].args[0])

    def test_it_asks_before_removing_and_respects_a_no(self):
        from bauh.cli import app

        with patch.object(web_legacy, 'leftovers', return_value=['/tmp/x']), \
                patch.object(web_legacy, 'installed_apps', return_value=['whatsapp']), \
                patch.object(web_legacy, 'remove') as remove, \
                patch('builtins.input', return_value='n'), patch('builtins.print'):
            self.assertEqual(1, app.clean_web_apps(assume_yes=False))

        remove.assert_not_called()

    def test_yes_removes_without_asking(self):
        from bauh.cli import app

        with patch.object(web_legacy, 'leftovers', return_value=['/tmp/x']), \
                patch.object(web_legacy, 'installed_apps', return_value=[]), \
                patch.object(web_legacy, 'remove', return_value=[]) as remove, \
                patch('builtins.input') as ask, patch('builtins.print'):
            self.assertEqual(0, app.clean_web_apps(assume_yes=True))

        remove.assert_called_once()
        ask.assert_not_called()

    def test_the_web_gem_is_gone(self):
        import importlib.util

        self.assertIsNone(importlib.util.find_spec('bauh.gems.web'))
