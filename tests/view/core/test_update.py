import os
import tempfile
from typing import Optional
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh.view.core import update
from bauh.view.core.update import (
    RELEASES_URL,
    check_for_update,
    find_latest_release,
    is_newer_release,
    parse_app_version,
    parse_release_tag,
)

I18N = {
    'warning.update_available': 'new {} version {} at {}',
    'tray.warning.update_available': 'new {} version {}',
}


def release(tag: str, draft: bool = False, prerelease: bool = False, html_url: Optional[str] = None) -> dict:
    return {'tag_name': tag, 'draft': draft, 'prerelease': prerelease,
            'html_url': html_url or f'https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases/tag/{tag}'}


class ParseReleaseTagTest(TestCase):

    def test_must_parse_fork_tags_with_gekko_suffix(self):
        self.assertEqual(((0, 10, 8), 1), parse_release_tag('v0.10.8-gekko.1'))
        self.assertEqual(((0, 10, 8), 12), parse_release_tag('v0.10.8-gekko.12'))
        self.assertEqual(((1, 0, 0), 3), parse_release_tag(' v1.0.0-gekko.3 '))

    def test_must_treat_tags_without_gekko_suffix_as_revision_zero(self):
        self.assertEqual(((0, 10, 7), 0), parse_release_tag('v0.10.7'))
        self.assertEqual(((0, 10, 7), 0), parse_release_tag('0.10.7'))

    def test_must_return_none_for_unknown_formats(self):
        for tag in (None, '', 'release', 'v0.10.8-gekko', 'v0.10.8-gekko.', 'v0.10.8+gekko.1', 'v0.10.8-rc1', 'vX.Y.Z'):
            self.assertIsNone(parse_release_tag(tag), tag)


class ParseAppVersionTest(TestCase):

    def test_must_parse_pep440_local_version(self):
        self.assertEqual(((0, 10, 8), 1), parse_app_version('0.10.8+gekko.1'))
        self.assertEqual(((0, 10, 8), 4), parse_app_version('0.10.8+gekko.4'))

    def test_must_treat_plain_version_as_revision_zero(self):
        self.assertEqual(((0, 10, 8), 0), parse_app_version('0.10.8'))

    def test_must_return_none_for_unknown_formats(self):
        for version in (None, '', 'v0.10.8', '0.10.8-gekko.1', '0.10.8.post1', 'abc'):
            self.assertIsNone(parse_app_version(version), version)


class IsNewerReleaseTest(TestCase):

    def test_fork_release_must_be_newer_than_plain_base_version(self):
        # __version__ todavía puede ser '0.10.8' (sin etiqueta local): el primer release del fork debe notificarse
        self.assertTrue(is_newer_release('v0.10.8-gekko.1', '0.10.8'))

    def test_same_release_must_not_be_newer(self):
        self.assertFalse(is_newer_release('v0.10.8-gekko.1', '0.10.8+gekko.1'))

    def test_higher_gekko_revision_must_be_newer(self):
        self.assertTrue(is_newer_release('v0.10.8-gekko.2', '0.10.8+gekko.1'))
        self.assertFalse(is_newer_release('v0.10.8-gekko.1', '0.10.8+gekko.2'))

    def test_higher_base_must_be_newer_regardless_of_revision(self):
        self.assertTrue(is_newer_release('v0.10.9-gekko.1', '0.10.8+gekko.7'))
        self.assertTrue(is_newer_release('v0.11.0', '0.10.8+gekko.7'))

    def test_tags_without_gekko_suffix_must_be_older_than_any_gekko_revision_of_the_same_base(self):
        self.assertFalse(is_newer_release('v0.10.8', '0.10.8+gekko.1'))
        self.assertFalse(is_newer_release('v0.10.7', '0.10.8'))

    def test_unknown_formats_must_not_be_considered_updates(self):
        self.assertFalse(is_newer_release('garbage', '0.10.8'))
        self.assertFalse(is_newer_release('v0.10.9', 'garbage'))
        self.assertFalse(is_newer_release(None, '0.10.8'))

    def test_must_use_the_application_version_by_default(self):
        with patch.object(update, '__version__', '0.10.8+gekko.1'):
            self.assertTrue(is_newer_release('v0.10.8-gekko.2'))
            self.assertFalse(is_newer_release('v0.10.8-gekko.1'))


class FindLatestReleaseTest(TestCase):

    def test_must_return_the_highest_published_release_not_the_first(self):
        releases = [release('v0.10.8-gekko.1'), release('v0.10.8-gekko.3'), release('v0.10.8-gekko.2')]
        self.assertEqual('v0.10.8-gekko.3', find_latest_release(releases)['tag_name'])

    def test_must_ignore_drafts_prereleases_and_unknown_tags(self):
        releases = [release('v0.10.9-gekko.1', draft=True),
                    release('v0.10.9-gekko.2', prerelease=True),
                    release('nightly'),
                    release('v0.10.8-gekko.1')]
        self.assertEqual('v0.10.8-gekko.1', find_latest_release(releases)['tag_name'])

    def test_must_return_none_when_nothing_is_usable(self):
        self.assertIsNone(find_latest_release([]))
        self.assertIsNone(find_latest_release(None))
        self.assertIsNone(find_latest_release([release('nightly'), release('v0.10.9-gekko.1', draft=True)]))
        self.assertIsNone(find_latest_release(['not-a-dict', {'draft': False}]))


class CheckForUpdateTest(TestCase):

    def setUp(self):
        self.cache_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache_dir.cleanup)

        patcher = patch.object(update, 'CACHE_DIR', self.cache_dir.name)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.logger = Mock()
        self.http_client = Mock()

    def test_must_query_the_fork_releases_and_not_the_upstream(self):
        self.assertIn('The-Gekko/Bauh-Fork-The-Gekko', RELEASES_URL)
        self.assertNotIn('vinifmor', RELEASES_URL)

        self.http_client.get_json.return_value = []
        check_for_update(self.logger, self.http_client, I18N)
        self.http_client.get_json.assert_called_once_with(RELEASES_URL)

    def test_must_notify_the_first_fork_release_when_the_version_has_no_gekko_suffix_yet(self):
        self.http_client.get_json.return_value = [release('v0.10.8-gekko.1')]

        with patch.object(update, '__version__', '0.10.8'):
            msg = check_for_update(self.logger, self.http_client, I18N)

        self.assertIsNotNone(msg)
        self.assertIn('v0.10.8-gekko.1', msg)
        self.assertIn('https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases/tag/v0.10.8-gekko.1', msg)
        self.assertTrue(os.path.isfile(f'{self.cache_dir.name}/updates/v0.10.8-gekko.1'))

    def test_must_not_notify_the_same_release_twice(self):
        self.http_client.get_json.return_value = [release('v0.10.8-gekko.2')]

        with patch.object(update, '__version__', '0.10.8+gekko.1'):
            self.assertIsNotNone(check_for_update(self.logger, self.http_client, I18N))
            self.assertIsNone(check_for_update(self.logger, self.http_client, I18N))

    def test_must_return_none_when_running_the_latest_release(self):
        self.http_client.get_json.return_value = [release('v0.10.8-gekko.1'), release('v0.10.7')]

        with patch.object(update, '__version__', '0.10.8+gekko.1'):
            self.assertIsNone(check_for_update(self.logger, self.http_client, I18N))

        self.assertFalse(os.path.exists(f'{self.cache_dir.name}/updates'))

    def test_must_ignore_historical_tags_without_gekko_suffix(self):
        self.http_client.get_json.return_value = [release('v0.10.7')]

        with patch.object(update, '__version__', '0.10.8'):
            self.assertIsNone(check_for_update(self.logger, self.http_client, I18N))

    def test_tray_message_must_use_its_own_notification_file(self):
        self.http_client.get_json.return_value = [release('v0.10.8-gekko.2')]

        with patch.object(update, '__version__', '0.10.8+gekko.1'):
            msg = check_for_update(self.logger, self.http_client, I18N, tray=True)

        self.assertEqual('new bauh version v0.10.8-gekko.2', msg)
        self.assertTrue(os.path.isfile(f'{self.cache_dir.name}/updates/tray_v0.10.8-gekko.2'))
        self.assertFalse(os.path.exists(f'{self.cache_dir.name}/updates/v0.10.8-gekko.2'))

    def test_must_return_none_when_the_api_fails(self):
        self.http_client.get_json.side_effect = Exception('offline')
        self.assertIsNone(check_for_update(self.logger, self.http_client, I18N))
        self.logger.error.assert_called()

    def test_must_return_none_when_the_api_returns_nothing(self):
        self.http_client.get_json.return_value = None
        self.assertIsNone(check_for_update(self.logger, self.http_client, I18N))
