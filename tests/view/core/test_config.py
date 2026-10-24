from unittest import TestCase
from unittest.mock import patch

from bauh.commons.config import YAMLConfigManager
from bauh.view.core.config import DEFAULT_THEME, RETIRED_THEMES, CoreConfigManager


class CoreConfigManagerTest(TestCase):

    def test_get_default_config__there_is_no_custom_theme_anymore(self):
        config = CoreConfigManager().get_default_config()

        self.assertNotIn('custom_theme', config)
        self.assertNotIn('custom_theme', config['ui'])

    def test_get_default_config__the_default_theme_must_be_aurora(self):
        config = CoreConfigManager().get_default_config()

        self.assertEqual('aurora', DEFAULT_THEME)
        self.assertEqual(DEFAULT_THEME, config['ui']['theme'])
        self.assertFalse(config['ui']['system_theme'])

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'theme': 'aurora', 'custom_theme': {'opacity': 75, 'enabled': True}},
        'custom_theme': {'opacity': 90, 'background_image': '/tmp/a.png'}
    })
    def test_read_config__an_old_custom_theme_is_discarded(self, read_config):
        config = CoreConfigManager().read_config()

        self.assertNotIn('custom_theme', config)
        self.assertNotIn('custom_theme', config['ui'])
        self.assertEqual('aurora', config['ui']['theme'])
        read_config.assert_called_once()


class RetiredThemesTest(TestCase):
    """Darcula, Knight y Sublime se retiraron: quien los tuviera elegidos pasa a Aurora."""

    def test_the_retired_themes_are_gone(self):
        from bauh.stylesheet import read_default_themes
        available = read_default_themes()

        for key in RETIRED_THEMES:
            self.assertNotIn(key, available)

        for key in ('aurora', 'light', 'gtk', 'matugen'):
            self.assertIn(key, available)

    def test_read_config__a_retired_theme_becomes_the_default_one(self):
        for key in RETIRED_THEMES:
            with patch.object(YAMLConfigManager, 'read_config', return_value={'ui': {'theme': key}}):
                config = CoreConfigManager().read_config()

            self.assertEqual(DEFAULT_THEME, config['ui']['theme'], key)

    def test_read_config__other_themes_are_kept(self):
        for key in ('light', 'matugen', '/home/user/.local/share/gekko-bauh/themes/mine.qss'):
            with patch.object(YAMLConfigManager, 'read_config', return_value={'ui': {'theme': key}}):
                config = CoreConfigManager().read_config()

            self.assertEqual(key, config['ui']['theme'])


class SuggestionsRemovedTest(TestCase):
    """Las sugerencias de paquetes se retiraron: sus listas no se tocaban desde 2022."""

    def test_the_default_config_has_no_suggestions(self):
        self.assertNotIn('suggestions', CoreConfigManager().get_default_config())

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'theme': 'aurora'}, 'suggestions': {'enabled': True, 'by_type': 15}
    })
    def test_read_config__the_old_suggestions_section_is_discarded(self, read_config):
        self.assertNotIn('suggestions', CoreConfigManager().read_config())

    def test_the_api_no_longer_asks_the_gems_for_suggestions(self):
        from bauh.api.abstract import model
        from bauh.api.abstract.controller import SoftwareManager

        self.assertFalse(hasattr(SoftwareManager, 'list_suggestions'))
        self.assertFalse(hasattr(model, 'PackageSuggestion'))
        self.assertFalse(hasattr(model, 'SuggestionPriority'))
