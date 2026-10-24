import glob
import os
from unittest import TestCase

from bauh.view.util import resource

# claves i18n de la ventana principal que tienen que existir, con texto, en todos los idiomas
REQUIRED_KEYS = (
    'manage_window.bt.matugen.text',
    'manage_window.bt.matugen.tip',
    'manage_window.filter.any_type',
    'manage_window.filter.any_category',
    'manage_window.table.empty.search',
    'manage_window.table.empty.updates',
    'manage_window.table.empty.filters',
    'manage_window.matugen.no_colors.title',
    'manage_window.matugen.no_colors.body',
    'manage_window.bt_themes.matugen.connect',
    'manage_window.bt_themes.matugen.connected',
    'manage_window.matugen.connect.title',
    'manage_window.matugen.connect.body',
    'manage_window.matugen.connect.done',
    'manage_window.matugen.connect.error'
)

# claves de funciones retiradas: si reaparecen es que alguien recuperó texto huérfano
RETIRED_KEY_PREFIXES = ('core.config.custom_theme', 'core.config.tab.custom_theme', 'core.config.download.check_ssl')


def read_locale(file_path: str) -> dict:
    """Lee un fichero de traducción con el formato 'clave=valor' por línea."""
    keys = {}

    with open(file_path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()

            if stripped and '=' in stripped:
                key, value = stripped.split('=', 1)
                keys[key.strip()] = value.strip()

    return keys


def locale_files() -> dict:
    locale_dir = resource.get_path('locale')
    return {os.path.basename(path): path for path in glob.glob(f'{locale_dir}/*')
            if os.path.isfile(path) and not path.endswith('.py')}


class UiLocaleKeysTest(TestCase):

    def test_every_locale_must_define_the_main_window_keys(self):
        files = locale_files()
        self.assertTrue(files)

        for locale_key, file_path in sorted(files.items()):
            keys = read_locale(file_path)

            for required in REQUIRED_KEYS:
                self.assertIn(required, keys, f"locale '{locale_key}' is missing '{required}'")
                self.assertTrue(keys[required], f"locale '{locale_key}' has an empty '{required}'")

    def test_the_matugen_button_label_must_be_the_same_everywhere(self):
        for locale_key, file_path in sorted(locale_files().items()):
            keys = read_locale(file_path)
            self.assertEqual('Matugen', keys['manage_window.bt.matugen.text'], locale_key)

    def test_the_values_must_not_contain_literal_escape_sequences(self):
        for locale_key, file_path in sorted(locale_files().items()):
            keys = read_locale(file_path)

            for required in REQUIRED_KEYS:
                self.assertNotIn('\\n', keys[required], f"locale '{locale_key}' / '{required}'")

    def test_the_placeholders_must_survive_the_translation(self):
        english = read_locale(locale_files()['en'])

        for locale_key, file_path in sorted(locale_files().items()):
            keys = read_locale(file_path)

            for required in REQUIRED_KEYS:
                self.assertEqual(english[required].count('{}'), keys[required].count('{}'),
                                 f"locale '{locale_key}' / '{required}'")

    def test_the_retired_features_left_no_keys_behind(self):
        for locale_key, file_path in sorted(locale_files().items()):
            leftovers = [k for k in read_locale(file_path) if k.startswith(RETIRED_KEY_PREFIXES)]
            self.assertEqual([], leftovers, locale_key)
