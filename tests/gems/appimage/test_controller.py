from unittest import TestCase
from unittest.mock import MagicMock

from bauh.gems.appimage import APP_REPOSITORY_URL
from bauh.gems.appimage.controller import AppImageManager


class AppImageManagerTest(TestCase):

    def setUp(self):
        self.manager = AppImageManager(context=MagicMock())

    def test_is_default_enabled__must_be_false_for_legacy_gems(self):
        self.assertFalse(self.manager.is_default_enabled())

    def test_app_repository__must_point_to_the_fork_and_not_to_the_upstream(self):
        self.assertEqual(APP_REPOSITORY_URL, self.manager.app_repository)
        self.assertIn('The-Gekko/Bauh-Fork-The-Gekko', self.manager.app_repository)
        self.assertNotIn('vinifmor', self.manager.app_repository)
