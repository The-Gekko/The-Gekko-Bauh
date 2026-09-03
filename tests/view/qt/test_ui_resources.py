import importlib.util
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), 'bauh', 'view', 'resources')
LOCALE_DIR = os.path.join(RESOURCES_DIR, 'locale')
IMG_DIR = os.path.join(RESOURCES_DIR, 'img')
PICTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), 'pictures')

LOCALE_KEYS = ('manage_window.close.transaction.title',
               'manage_window.close.transaction.body',
               'manage_window.error.unexpected.body')

if PYQT5_AVAILABLE:
    from PyQt5.QtWidgets import QApplication

    from bauh.view.qt import about
    from bauh.view.qt.components.inputs import InputFilter
    from bauh.view.util import util


def read_locale(path: str) -> dict:
    keys = {}

    with open(path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()

            if stripped:
                key, _, value = stripped.partition('=')
                keys[key.strip()] = value.strip()

    return keys


class TestLocales(unittest.TestCase):

    LANGUAGES = ('ca', 'de', 'en', 'es', 'fr', 'it', 'pt', 'ru', 'tr', 'zh')

    def test_new_manage_window_keys_are_translated_in_every_language(self):
        for lang in self.LANGUAGES:
            keys = read_locale(os.path.join(LOCALE_DIR, lang))

            for key in LOCALE_KEYS:
                with self.subTest(lang=lang, key=key):
                    self.assertIn(key, keys)
                    self.assertTrue(keys[key], f"'{key}' is empty in '{lang}'")

    def test_new_keys_have_no_literal_escape_sequences(self):
        for lang in self.LANGUAGES:
            keys = read_locale(os.path.join(LOCALE_DIR, lang))

            for key in LOCALE_KEYS:
                with self.subTest(lang=lang, key=key):
                    self.assertNotIn('\\n', keys[key])

    def test_about_fork_key_is_translated_in_every_language(self):
        about_dir = os.path.join(LOCALE_DIR, 'about')

        for lang in os.listdir(about_dir):
            path = os.path.join(about_dir, lang)

            if not os.path.isfile(path) or lang.endswith('.py'):
                continue

            with self.subTest(lang=lang):
                keys = read_locale(path)
                self.assertIn('about.info.fork', keys)
                self.assertIn('{}', keys['about.info.fork'])


class TestIconResources(unittest.TestCase):

    def test_the_default_icon_is_not_oversized(self):
        path = os.path.join(IMG_DIR, 'gekko-bauh.png')
        self.assertTrue(os.path.isfile(path))
        # el original de 1024x1024 pesaba 1,28 MB y se decodificaba varias veces por arranque
        self.assertLess(os.path.getsize(path), 200 * 1024)

    def test_there_is_a_distinct_icon_for_the_updates_state(self):
        default_icon = os.path.join(IMG_DIR, 'gekko-bauh.png')
        update_icon = os.path.join(IMG_DIR, 'gekko-bauh-update.png')
        self.assertTrue(os.path.isfile(update_icon))

        with open(default_icon, 'rb') as f:
            default_content = f.read()

        with open(update_icon, 'rb') as f:
            update_content = f.read()

        self.assertNotEqual(default_content, update_content)

    def test_the_icon_set_is_complete(self):
        for size in (16, 32, 48, 64, 128, 256, 512):
            with self.subTest(size=size):
                self.assertTrue(os.path.isfile(os.path.join(PICTURES_DIR, 'icons', f'gekko-bauh-{size}.png')))

    def test_the_original_picture_is_preserved(self):
        self.assertTrue(os.path.isfile(os.path.join(PICTURES_DIR, 'gekko-bauh.png')))


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestDefaultIcon(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_system_icon_has_priority_when_requested(self):
        system_icon = MagicMock()
        system_icon.isNull.return_value = False
        system_icon.name.return_value = 'bauh'

        with patch('bauh.view.util.util.QIcon') as qicon:
            qicon.fromTheme.return_value = system_icon
            path, icon = util.get_default_icon(system=True)

        self.assertEqual('bauh', path)
        self.assertIs(system_icon, icon)

    def test_the_bundled_icon_is_used_when_the_system_has_none(self):
        util._cached_icon.cache_clear()
        null_icon = MagicMock()
        null_icon.isNull.return_value = True

        with patch('bauh.view.util.util.QIcon') as qicon:
            qicon.fromTheme.return_value = null_icon
            path, _ = util.get_default_icon(system=True)

        self.assertTrue(path.endswith('img/gekko-bauh.png'))

    def test_the_icon_is_cached_by_path(self):
        util._cached_icon.cache_clear()
        first = util._cached_icon('/tmp/does-not-matter.png')
        second = util._cached_icon('/tmp/does-not-matter.png')
        self.assertIs(first, second)


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestAboutDialogUrls(unittest.TestCase):

    def test_the_urls_point_to_the_fork_and_the_upstream(self):
        self.assertIn('The-Gekko/Bauh-Fork-The-Gekko', about.PROJECT_URL)
        self.assertIn('The-Gekko/Bauh-Fork-The-Gekko', about.LICENSE_URL)
        self.assertEqual('https://github.com/vinifmor/bauh', about.UPSTREAM_URL)

    def test_the_display_name_identifies_the_fork(self):
        self.assertEqual('bauh Gekko Edition', about.get_display_name())


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestInputFilter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_typing_timer_does_not_repeat(self):
        inp = InputFilter(on_key_press=lambda: None)
        self.assertTrue(inp.typing.isSingleShot())
        self.assertFalse(inp.typing.isActive())
        self.assertLessEqual(InputFilter.TYPING_DELAY, 1000)


if __name__ == '__main__':
    unittest.main()
