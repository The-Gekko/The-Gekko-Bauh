import glob
import importlib.util
import os
import unittest
from unittest import TestCase

from bauh.view.util import resource

# claves i18n que la pestaña «Personalización» y el botón Matugen necesitan en todos los idiomas
REQUIRED_KEYS = (
    'core.config.tab.custom_theme',
    'core.config.custom_theme.enabled',
    'core.config.custom_theme.enabled.tip',
    'core.config.custom_theme.bg_color',
    'core.config.custom_theme.bg_color.tip',
    'core.config.custom_theme.text_color',
    'core.config.custom_theme.text_color.tip',
    'core.config.custom_theme.accent_color',
    'core.config.custom_theme.accent_color.tip',
    'core.config.custom_theme.opacity',
    'core.config.custom_theme.opacity.tip',
    'core.config.custom_theme.bg_image',
    'core.config.custom_theme.bg_image.tip',
    'core.config.custom_theme.reset',
    'core.config.custom_theme.reset.tip',
    'manage_window.bt.matugen.text',
    'manage_window.bt.matugen.tip'
)

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None


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


class CustomThemeLocaleTest(TestCase):

    def test_every_locale_must_define_the_custom_theme_keys(self):
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

    def test_the_new_values_must_not_contain_literal_escape_sequences(self):
        for locale_key, file_path in sorted(locale_files().items()):
            keys = read_locale(file_path)

            for required in REQUIRED_KEYS:
                self.assertNotIn('\\n', keys[required], f"locale '{locale_key}' / '{required}'")


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class CustomThemeSettingsTabTest(TestCase):

    def _new_manager(self):
        from bauh.view.core.settings import GenericSettingsManager
        from bauh.view.util.translation import I18n

        manager = object.__new__(GenericSettingsManager)
        english = read_locale(locale_files()['en'])
        manager.i18n = I18n('en', english, 'en', english)
        return manager

    def test_the_tab_must_use_the_i18n_keys(self):
        from bauh.api.abstract.view import FormComponent, PanelComponent
        from bauh.view.core.config import DEFAULT_CUSTOM_THEME

        manager = self._new_manager()
        english = read_locale(locale_files()['en'])
        tab = manager._gen_custom_theme_settings({'custom_theme': dict(DEFAULT_CUSTOM_THEME)})

        self.assertEqual(english['core.config.tab.custom_theme'].capitalize(), tab.label)

        form = tab.get_content(PanelComponent).get_component_by_idx(0, FormComponent)
        labels = {component.label for component in form.components}

        for key in ('core.config.custom_theme.enabled', 'core.config.custom_theme.bg_color',
                    'core.config.custom_theme.text_color', 'core.config.custom_theme.accent_color',
                    'core.config.custom_theme.opacity', 'core.config.custom_theme.bg_image',
                    'core.config.custom_theme.reset'):
            self.assertIn(english[key], labels, key)

        # ninguna etiqueta puede ser la clave sin traducir ni el texto en español codificado a mano
        for label in labels:
            self.assertNotIn('core.config.custom_theme', label)
            self.assertNotEqual('Habilitar Personalización', label)

    def test_the_tab_must_show_the_stored_values(self):
        from bauh.api.abstract.view import FormComponent, PanelComponent

        manager = self._new_manager()
        config = {'custom_theme': {'enabled': True, 'background_color': '#010203',
                                   'text_color': '#040506', 'accent_color': '#070809',
                                   'opacity': 42, 'background_image': None}}

        tab = manager._gen_custom_theme_settings(config)
        form = tab.get_content(PanelComponent).get_component_by_idx(0, FormComponent)

        self.assertEqual('#010203', form.get_component('ct_bg').value)
        self.assertEqual('#040506', form.get_component('ct_text').value)
        self.assertEqual('#070809', form.get_component('ct_acc').value)
        self.assertEqual(42, form.get_component('ct_opacity').value)
        self.assertTrue(form.get_component('ct_enabled').get_selected())
