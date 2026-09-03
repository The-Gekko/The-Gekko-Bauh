import os
import shutil
import tempfile
import unittest

from bauh.gems.github.build_detector import (
    BUILD_COMMANDS,
    SUPPORTED_METHODS,
    BuildMethod,
    detect_build_method,
    get_required_binary,
    is_supported,
    method_from_value,
    requires_root,
    uninstall_command,
    uninstall_requires_root,
)


class BuildDetectionTest(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix='bauh-github-test-')

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def _touch(self, *names):
        for name in names:
            with open(os.path.join(self.repo, name), 'w') as handle:
                handle.write('')

    def test_detect__unknown_when_the_path_does_not_exist(self):
        method, command = detect_build_method(os.path.join(self.repo, 'missing'))

        self.assertEqual(BuildMethod.UNKNOWN, method)
        self.assertIsNone(command)

    def test_detect__unknown_for_an_empty_repository(self):
        method, command = detect_build_method(self.repo)

        self.assertEqual(BuildMethod.UNKNOWN, method)
        self.assertIsNone(command)

    def test_detect__unknown_for_a_none_path(self):
        self.assertEqual((BuildMethod.UNKNOWN, None), detect_build_method(None))

    def test_detect__pkgbuild_wins_over_everything_else(self):
        self._touch('PKGBUILD', 'Makefile', 'setup.py', 'Cargo.toml', 'CMakeLists.txt')

        method, command = detect_build_method(self.repo)

        self.assertEqual(BuildMethod.PKGBUILD, method)
        self.assertEqual('makepkg -s --noconfirm', command)

    def test_detect__python_wins_over_makefile(self):
        # un proyecto de Python con Makefile de conveniencia debe instalarse con pipx,
        # que es la vía que después se puede desinstalar
        self._touch('pyproject.toml', 'Makefile')

        method, _ = detect_build_method(self.repo)

        self.assertEqual(BuildMethod.PYTHON_SETUP, method)

    def test_detect__cargo_wins_over_makefile(self):
        self._touch('Cargo.toml', 'Makefile')

        method, _ = detect_build_method(self.repo)

        self.assertEqual(BuildMethod.CARGO, method)

    def test_detect__setup_py_is_python(self):
        self._touch('setup.py')

        self.assertEqual(BuildMethod.PYTHON_SETUP, detect_build_method(self.repo)[0])

    def test_detect__makefile_variants(self):
        for name in ('Makefile', 'makefile', 'GNUmakefile'):
            with self.subTest(name=name):
                repo = tempfile.mkdtemp(prefix='bauh-github-test-')

                try:
                    with open(os.path.join(repo, name), 'w') as handle:
                        handle.write('')

                    method, command = detect_build_method(repo)
                    self.assertEqual(BuildMethod.MAKEFILE, method)
                    self.assertIsNone(command)
                finally:
                    shutil.rmtree(repo, ignore_errors=True)

    def test_detect__meson_and_cmake_have_no_command(self):
        self._touch('meson.build')
        self.assertEqual((BuildMethod.MESON, None), detect_build_method(self.repo))

    def test_detect__install_script_has_no_command(self):
        self._touch('install.sh')

        method, command = detect_build_method(self.repo)

        self.assertEqual(BuildMethod.INSTALL_SCRIPT, method)
        self.assertIsNone(command)


class BuildCommandsTest(unittest.TestCase):

    def test_python_command__must_use_pipx_and_never_break_system_packages(self):
        command = BUILD_COMMANDS[BuildMethod.PYTHON_SETUP][0]

        self.assertEqual('pipx install .', command)
        self.assertNotIn('--break-system-packages', command)
        self.assertNotIn('pip install', command)

    def test_cargo_command__must_not_compile_twice(self):
        command = BUILD_COMMANDS[BuildMethod.CARGO][0]

        self.assertEqual('cargo install --path . --locked', command)
        self.assertNotIn('cargo build', command)

    def test_pkgbuild_command__must_not_install_from_makepkg(self):
        # 'makepkg -si' invoca pacman y falla sin terminal; la instalación se hace aparte
        command = BUILD_COMMANDS[BuildMethod.PKGBUILD][0]

        self.assertEqual('makepkg -s --noconfirm', command)
        self.assertNotIn('-si', command)

    def test_requires_root__only_the_pkgbuild_install_step(self):
        self.assertTrue(requires_root(BuildMethod.PKGBUILD))
        self.assertFalse(requires_root(BuildMethod.PYTHON_SETUP))
        self.assertFalse(requires_root(BuildMethod.CARGO))
        self.assertFalse(requires_root(BuildMethod.MAKEFILE))
        self.assertFalse(requires_root(BuildMethod.UNKNOWN))

    def test_supported_methods(self):
        self.assertEqual({BuildMethod.PKGBUILD, BuildMethod.PYTHON_SETUP, BuildMethod.CARGO},
                         set(SUPPORTED_METHODS))

        for method in (BuildMethod.MAKEFILE, BuildMethod.INSTALL_SCRIPT, BuildMethod.MESON,
                       BuildMethod.CMAKE, BuildMethod.UNKNOWN):
            self.assertFalse(is_supported(method))

    def test_required_binaries(self):
        self.assertEqual('makepkg', get_required_binary(BuildMethod.PKGBUILD))
        self.assertEqual('pipx', get_required_binary(BuildMethod.PYTHON_SETUP))
        self.assertEqual('cargo', get_required_binary(BuildMethod.CARGO))
        self.assertIsNone(get_required_binary(BuildMethod.UNKNOWN))

    def test_method_from_value(self):
        self.assertEqual(BuildMethod.PKGBUILD, method_from_value('PKGBUILD'))
        self.assertEqual(BuildMethod.CARGO, method_from_value('Cargo (Rust)'))
        self.assertEqual(BuildMethod.UNKNOWN, method_from_value(None))
        self.assertEqual(BuildMethod.UNKNOWN, method_from_value('something else'))


class UninstallCommandTest(unittest.TestCase):

    def test_pkgbuild__must_remove_with_pacman(self):
        self.assertEqual(['pacman', '-R', '--noconfirm', 'ripgrep'],
                         uninstall_command(BuildMethod.PKGBUILD, ['ripgrep']))

    def test_python__must_remove_with_pipx(self):
        self.assertEqual(['pipx', 'uninstall', 'black'],
                         uninstall_command(BuildMethod.PYTHON_SETUP, ['black']))

    def test_cargo__must_remove_with_cargo(self):
        self.assertEqual(['cargo', 'uninstall', 'ripgrep'],
                         uninstall_command(BuildMethod.CARGO, ['ripgrep']))

    def test_no_command_without_artifacts(self):
        self.assertIsNone(uninstall_command(BuildMethod.PKGBUILD, []))
        self.assertIsNone(uninstall_command(BuildMethod.PKGBUILD, None))
        self.assertIsNone(uninstall_command(BuildMethod.UNKNOWN, ['x']))

    def test_uninstall_requires_root(self):
        self.assertTrue(uninstall_requires_root(BuildMethod.PKGBUILD))
        self.assertFalse(uninstall_requires_root(BuildMethod.PYTHON_SETUP))
        self.assertFalse(uninstall_requires_root(BuildMethod.CARGO))


if __name__ == '__main__':
    unittest.main()
