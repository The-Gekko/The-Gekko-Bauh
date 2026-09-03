import os
import shutil
import tempfile
import unittest

from bauh.gems.github import registry

PIPX_OUTPUT = """  installed package black 23.1.0, installed using Python 3.11
  These apps are now globally available
    - black
done!
"""

CARGO_OUTPUT = """  Installing ripgrep v13.0.0 (/home/user/repos/ripgrep)
   Compiling ripgrep v13.0.0
    Finished release [optimized] target(s) in 45.2s
  Installing /home/user/.cargo/bin/rg
   Installed package `ripgrep v13.0.0` (executable `rg`)
"""

CARGO_TOML = """[package]
name = "ripgrep"
version = "13.0.0"

[dependencies]
name = "not-this-one"
"""


class ArtifactParsingTest(unittest.TestCase):

    def test_pacman_package_name(self):
        self.assertEqual('ripgrep', registry.parse_pacman_package_name(
            'ripgrep-13.0.0-1-x86_64.pkg.tar.zst'))

    def test_pacman_package_name__with_a_dashed_name(self):
        self.assertEqual('my-tool-git', registry.parse_pacman_package_name(
            'my-tool-git-r120.abcdef-1-any.pkg.tar.zst'))

    def test_pacman_package_name__full_path(self):
        self.assertEqual('ripgrep', registry.parse_pacman_package_name(
            '/tmp/repos/owner/ripgrep/ripgrep-13.0.0-1-x86_64.pkg.tar.xz'))

    def test_pacman_package_name__not_a_package(self):
        self.assertIsNone(registry.parse_pacman_package_name('README.md'))
        self.assertIsNone(registry.parse_pacman_package_name(''))

    def test_pacman_package_names__deduplicates(self):
        names = registry.parse_pacman_package_names([
            'ripgrep-13.0.0-1-x86_64.pkg.tar.zst',
            'ripgrep-13.0.0-1-x86_64.pkg.tar.zst',
            'ripgrep-debug-13.0.0-1-x86_64.pkg.tar.zst',
            'not-a-package.txt'])

        self.assertEqual(['ripgrep', 'ripgrep-debug'], names)

    def test_pipx_installed_names(self):
        self.assertEqual(['black'], registry.parse_pipx_installed_names(PIPX_OUTPUT))

    def test_pipx_installed_names__empty_output(self):
        self.assertEqual([], registry.parse_pipx_installed_names(''))
        self.assertEqual([], registry.parse_pipx_installed_names(None))

    def test_cargo_installed_names(self):
        self.assertEqual(['ripgrep'], registry.parse_cargo_installed_names(CARGO_OUTPUT))

    def test_cargo_package_name_from_manifest(self):
        self.assertEqual('ripgrep', registry.read_cargo_package_name(CARGO_TOML))

    def test_cargo_package_name__no_package_section(self):
        self.assertIsNone(registry.read_cargo_package_name('[dependencies]\nname = "x"\n'))
        self.assertIsNone(registry.read_cargo_package_name(None))


class InstallationRegistryTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-registry-')
        self.registry = registry.InstallationRegistry(
            file_path=os.path.join(self.dir, 'cache', 'installed.json'))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_key_for(self):
        self.assertEqual('owner/repo',
                         registry.InstallationRegistry.key_for('owner', 'repo'))

    def test_read__empty_when_the_file_does_not_exist(self):
        self.assertEqual({}, self.registry.read())
        self.assertIsNone(self.registry.get('owner/repo'))

    def test_record_and_get(self):
        self.registry.record('owner/repo', 'PKGBUILD', ['ripgrep'], '/repos/owner/repo',
                             'https://github.com/owner/repo')
        record = self.registry.get('owner/repo')

        self.assertEqual('PKGBUILD', record['build_method'])
        self.assertEqual(['ripgrep'], record['artifacts'])
        self.assertEqual('/repos/owner/repo', record['clone_path'])

    def test_record__must_survive_a_new_instance(self):
        self.registry.record('owner/repo', 'Cargo (Rust)', ['ripgrep'])
        other = registry.InstallationRegistry(file_path=self.registry.file_path)

        self.assertEqual(['ripgrep'], other.get('owner/repo')['artifacts'])

    def test_remove(self):
        self.registry.record('owner/repo', 'PKGBUILD', ['ripgrep'])
        self.assertTrue(self.registry.remove('owner/repo'))
        self.assertIsNone(self.registry.get('owner/repo'))

    def test_remove__unknown_key_is_not_an_error(self):
        self.assertTrue(self.registry.remove('nobody/nothing'))

    def test_clear(self):
        self.registry.record('owner/repo', 'PKGBUILD', ['ripgrep'])
        self.assertTrue(self.registry.clear())
        self.assertEqual({}, self.registry.read())

    def test_read__corrupted_file_returns_empty(self):
        os.makedirs(os.path.dirname(self.registry.file_path), exist_ok=True)

        with open(self.registry.file_path, 'w') as handle:
            handle.write('{not json')

        self.assertEqual({}, self.registry.read())


if __name__ == '__main__':
    unittest.main()
