import os
import stat
import tempfile
import unittest
from getpass import getuser

from bauh import __app_name__
from bauh.api import paths


def _mode(path: str) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


class PrivateDirTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test__ensure_private_dir_must_create_the_directory_with_mode_0700(self):
        path = os.path.join(self.tmp.name, 'a', 'b')

        self.assertTrue(paths.ensure_private_dir(path))
        self.assertTrue(os.path.isdir(path))
        self.assertEqual(0o700, _mode(path))
        self.assertTrue(paths.is_private_dir(path))

    def test__ensure_private_dir_must_fix_the_permissions_of_an_owned_directory(self):
        path = os.path.join(self.tmp.name, 'open')
        os.mkdir(path)
        os.chmod(path, 0o755)

        self.assertTrue(paths.ensure_private_dir(path))
        self.assertEqual(0o700, _mode(path))

    def test__ensure_private_dir_must_reject_symbolic_links(self):
        target = os.path.join(self.tmp.name, 'target')
        os.mkdir(target, 0o700)
        link = os.path.join(self.tmp.name, 'link')
        os.symlink(target, link)

        self.assertFalse(paths.ensure_private_dir(link))
        self.assertFalse(paths.is_private_dir(link))

    def test__ensure_private_dir_must_reject_regular_files(self):
        path = os.path.join(self.tmp.name, 'file')
        with open(path, 'w') as f:
            f.write('x')

        self.assertFalse(paths.ensure_private_dir(path))
        self.assertFalse(paths.is_private_dir(path))

    def test__is_private_dir_must_reject_directories_accessible_by_group_or_others(self):
        path = os.path.join(self.tmp.name, 'shared')
        os.mkdir(path)
        os.chmod(path, 0o750)
        self.assertFalse(paths.is_private_dir(path))

        os.chmod(path, 0o700)
        self.assertTrue(paths.is_private_dir(path))

    def test__is_private_dir_must_return_false_for_missing_paths(self):
        self.assertFalse(paths.is_private_dir(os.path.join(self.tmp.name, 'missing')))


class ResolvePrivateTempDirTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test__must_return_the_preferred_dir_when_it_can_be_secured(self):
        preferred = os.path.join(self.tmp.name, 'tmp')

        self.assertEqual(preferred, paths.resolve_private_temp_dir(preferred))
        self.assertTrue(paths.is_private_dir(preferred))

    def test__must_fall_back_to_a_random_private_dir_when_the_preferred_one_is_a_symlink(self):
        target = os.path.join(self.tmp.name, 'target')
        os.mkdir(target, 0o700)
        preferred = os.path.join(self.tmp.name, 'tmp')
        os.symlink(target, preferred)

        resolved = paths.resolve_private_temp_dir(preferred)
        self.addCleanup(os.rmdir, resolved)

        self.assertNotEqual(preferred, resolved)
        self.assertTrue(paths.is_private_dir(resolved))
        self.assertTrue(os.path.basename(resolved).startswith(f'{__app_name__}-'))


class TempDirConstantsTest(unittest.TestCase):

    def test__temp_dir_must_not_be_the_predictable_path_in_the_shared_tmp(self):
        self.assertNotEqual(f'/tmp/{__app_name__}@{getuser()}', paths.TEMP_DIR)
        self.assertFalse(paths.TEMP_DIR.startswith(f'/tmp/{__app_name__}@'))

    def test__temp_dir_must_be_the_cache_tmp_dir_or_a_random_private_dir(self):
        self.assertTrue(paths.TEMP_DIR == f'{paths.CACHE_DIR}/tmp'
                        or os.path.basename(paths.TEMP_DIR).startswith(f'{__app_name__}-'), paths.TEMP_DIR)

    def test__temp_dir_must_be_private_to_the_current_user(self):
        self.assertTrue(paths.is_private_dir(paths.TEMP_DIR), paths.TEMP_DIR)

    def test__get_temp_dir_must_return_the_same_dir_for_the_current_user(self):
        self.assertEqual(paths.TEMP_DIR, paths.get_temp_dir())
        self.assertEqual(paths.TEMP_DIR, paths.get_temp_dir(getuser()))

    def test__get_temp_dir_must_keep_the_legacy_path_for_other_users(self):
        self.assertEqual(f'/tmp/{__app_name__}@{__app_name__}-aur', paths.get_temp_dir(f'{__app_name__}-aur'))

    def test__logs_dir_must_live_under_the_user_cache_dir(self):
        self.assertEqual(f'{paths.CACHE_DIR}/logs', paths.LOGS_DIR)
