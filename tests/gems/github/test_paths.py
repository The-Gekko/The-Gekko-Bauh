import os
import shutil
import tempfile
import unittest

from bauh.gems.github import paths

# nombres que nunca deben aceptarse como componente de una ruta local
MALICIOUS_NAMES = ('..', '.', '../../etc', 'foo/bar', 'foo\\bar', '.git', '', None,
                   '/etc/passwd', '.ssh', '..%2f..', ' ', 'a b')


class RepoComponentValidationTest(unittest.TestCase):

    def test_valid_names(self):
        for name in ('bauh', 'The-Gekko', 'repo_name', 'repo.name', 'a', '0ad'):
            with self.subTest(name=name):
                self.assertTrue(paths.is_valid_repo_component(name))

    def test_malicious_names_must_be_rejected(self):
        for name in MALICIOUS_NAMES:
            with self.subTest(name=name):
                self.assertFalse(paths.is_valid_repo_component(name))

    def test_a_name_starting_with_a_dot_must_be_rejected(self):
        self.assertFalse(paths.is_valid_repo_component('.hidden'))

    def test_non_string_values_must_be_rejected(self):
        self.assertFalse(paths.is_valid_repo_component(12))
        self.assertFalse(paths.is_valid_repo_component(['a']))

    def test_normalize_repo_name(self):
        self.assertEqual('bauh', paths.normalize_repo_name('bauh.git'))
        self.assertEqual('bauh', paths.normalize_repo_name('bauh'))
        self.assertIsNone(paths.normalize_repo_name(None))


class ClonePathTest(unittest.TestCase):

    def test_clone_path__must_include_the_owner(self):
        self.assertEqual('/repos/owner1/dotfiles',
                         paths.build_clone_path('/repos', 'owner1', 'dotfiles'))

    def test_clone_path__two_owners_never_collide(self):
        first = paths.build_clone_path('/repos', 'owner1', 'dotfiles')
        second = paths.build_clone_path('/repos', 'owner2', 'dotfiles')

        self.assertNotEqual(first, second)

    def test_clone_path__must_drop_the_git_suffix(self):
        self.assertEqual('/repos/owner/bauh',
                         paths.build_clone_path('/repos', 'owner', 'bauh.git'))

    def test_clone_path__must_reject_a_malicious_repo_name(self):
        for name in MALICIOUS_NAMES:
            with self.subTest(name=name):
                self.assertIsNone(paths.build_clone_path('/repos', 'owner', name))

    def test_clone_path__must_reject_a_malicious_owner(self):
        for name in MALICIOUS_NAMES:
            with self.subTest(name=name):
                self.assertIsNone(paths.build_clone_path('/repos', name, 'repo'))

    def test_clone_path__without_repos_dir(self):
        self.assertIsNone(paths.build_clone_path('', 'owner', 'repo'))


class ContainmentTest(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='bauh-github-paths-')

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_is_inside__a_child_directory(self):
        child = os.path.join(self.base, 'owner', 'repo')
        os.makedirs(child)

        self.assertTrue(paths.is_inside(self.base, child))

    def test_is_inside__the_base_itself_is_not_inside(self):
        self.assertFalse(paths.is_inside(self.base, self.base))

    def test_is_inside__an_outside_path(self):
        self.assertFalse(paths.is_inside(self.base, os.path.expanduser('~')))
        self.assertFalse(paths.is_inside(self.base, '/etc'))

    def test_is_inside__a_traversal_must_be_resolved(self):
        escaped = os.path.join(self.base, '..', '..', 'etc')

        self.assertFalse(paths.is_inside(self.base, escaped))

    def test_is_inside__a_symlink_pointing_outside_must_be_rejected(self):
        outside = tempfile.mkdtemp(prefix='bauh-github-outside-')
        link = os.path.join(self.base, 'link')

        try:
            os.symlink(outside, link)
            self.assertFalse(paths.is_inside(self.base, link))
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_is_safe_clone_path__requires_a_git_directory(self):
        clone = os.path.join(self.base, 'owner', 'repo')
        os.makedirs(clone)

        self.assertFalse(paths.is_safe_clone_path(self.base, clone))

        os.makedirs(os.path.join(clone, '.git'))
        self.assertTrue(paths.is_safe_clone_path(self.base, clone))

    def test_is_safe_clone_path__rejects_the_home_directory(self):
        self.assertFalse(paths.is_safe_clone_path(self.base, os.path.expanduser('~')))

    def test_is_safe_clone_path__rejects_none(self):
        self.assertFalse(paths.is_safe_clone_path(self.base, None))


if __name__ == '__main__':
    unittest.main()
