from unittest import TestCase
from unittest.mock import patch

from bauh.commons.config import YAMLConfigManager
from bauh.view.core.config import DEFAULT_CUSTOM_THEME, DEFAULT_THEME, CoreConfigManager


class CoreConfigManagerTest(TestCase):

    def test_get_default_config__must_store_custom_theme_at_the_root_level(self):
        config = CoreConfigManager().get_default_config()

        self.assertIn('custom_theme', config)
        self.assertNotIn('custom_theme', config['ui'])

    def test_get_default_config__the_default_theme_must_be_aurora(self):
        config = CoreConfigManager().get_default_config()

        self.assertEqual('aurora', DEFAULT_THEME)
        self.assertEqual(DEFAULT_THEME, config['ui']['theme'])
        self.assertFalse(config['ui']['system_theme'])

    def test_get_default_config__custom_theme_must_declare_enabled(self):
        config = CoreConfigManager().get_default_config()

        self.assertIn('enabled', config['custom_theme'])
        self.assertFalse(config['custom_theme']['enabled'])

    def test_get_default_config__custom_theme_must_come_from_the_single_source_of_truth(self):
        config = CoreConfigManager().get_default_config()

        self.assertEqual(DEFAULT_CUSTOM_THEME, config['custom_theme'])
        self.assertIsNot(DEFAULT_CUSTOM_THEME, config['custom_theme'])

    def test_get_default_config__custom_theme_must_not_share_state_between_calls(self):
        first = CoreConfigManager().get_default_config()
        first['custom_theme']['opacity'] = 10

        second = CoreConfigManager().get_default_config()

        self.assertEqual(100, second['custom_theme']['opacity'])
        self.assertEqual(100, DEFAULT_CUSTOM_THEME['opacity'])

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'custom_theme': {'opacity': 75, 'enabled': True}}
    })
    def test_read_config__must_migrate_legacy_custom_theme(self, read_config):
        config = CoreConfigManager().read_config()

        self.assertNotIn('custom_theme', config['ui'])
        self.assertEqual({'opacity': 75, 'enabled': True}, config['custom_theme'])
        read_config.assert_called_once()

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'custom_theme': {'opacity': 75}},
        'custom_theme': {'opacity': 90}
    })
    def test_read_config__must_preserve_a_root_custom_theme(self, read_config):
        config = CoreConfigManager().read_config()

        self.assertNotIn('custom_theme', config['ui'])
        self.assertEqual({'opacity': 90}, config['custom_theme'])
        read_config.assert_called_once()
