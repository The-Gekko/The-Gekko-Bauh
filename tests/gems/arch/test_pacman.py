import os
import warnings
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, Mock

from bauh import __package_name__
from bauh.gems.arch import pacman

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class PacmanTest(TestCase):

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    def test_list_ignored_packages(self):
        ignored = pacman.list_ignored_packages(FILE_DIR + '/resources/pacman_ign_pkgs.conf')

        self.assertIsNotNone(ignored)
        self.assertEqual(2, len(ignored))
        self.assertIn('google-chrome', ignored)
        self.assertIn('firefox', ignored)

    def test_list_ignored_packages__no_ignored_packages(self):
        ignored = pacman.list_ignored_packages(FILE_DIR + '/resources/pacman.conf')

        self.assertIsNotNone(ignored)
        self.assertEqual(0, len(ignored))

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value="""
Name            : package-test
Version         : 3.4.4-1
Description     : Test
Depends On      : embree  freetype2  libglvnd
Optional Deps   : lib32-vulkan-icd-loader: Vulkan support [installed]
Required By     : None
            """)
    def test_map_optional_deps__no_remote_and_not_installed__only_one_installed_with_description(self, run: Mock):
        res = pacman.map_optional_deps(('package-test',), remote=False, not_installed=True)
        run.assert_called_once_with(['pacman', '-Qi', 'package-test'])
        self.assertEqual({'package-test': {}}, res)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value="""
Name            : package-test
Version         : 3.4.4-1
Description     : Test
Depends On      : embree  freetype2  libglvnd
Optional Deps   : lib32-vulkan-icd-loader: Vulkan support
Required By     : None
        """)
    def test_map_optional_deps__no_remote_and_not_installed__only_one_not_installed_with_description(self, run: Mock):
        res = pacman.map_optional_deps(('package-test',), remote=False, not_installed=True)
        run.assert_called_once_with(['pacman', '-Qi', 'package-test'])
        self.assertEqual({'package-test': {'lib32-vulkan-icd-loader': 'Vulkan support'}}, res)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value="""
Name            : package-test
Version         : 3.4.4-1
Description     : Test
Depends On      : embree  freetype2  libglvnd
Optional Deps   : pipewire-alsa
Required By     : None
            """)
    def test_map_optional_deps__no_remote_and_not_installed__only_one_not_installed_no_description(self, run: Mock):
        res = pacman.map_optional_deps(('package-test',), remote=False, not_installed=True)
        run.assert_called_once_with(['pacman', '-Qi', 'package-test'])
        self.assertEqual({'package-test': {'pipewire-alsa': ''}}, res)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value="""
Name            : package-test
Version         : 3.4.4-1
Description     : Test
Depends On      : embree  freetype2  libglvnd
Optional Deps   : pipewire-alsa [installed]
Required By     : None
                """)
    def test_map_optional_deps__no_remote_and_not_installed__only_one_installed_no_description(self, run: Mock):
        res = pacman.map_optional_deps(('package-test',), remote=False, not_installed=True)
        run.assert_called_once_with(['pacman', '-Qi', 'package-test'])
        self.assertEqual({'package-test': {}}, res)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value="""
Name            : package-test
Version         : 3.4.4-1
Description     : Test
Depends On      : embree  freetype2  libglvnd  libtheora
Optional Deps   : pipewire-alsa
                  pipewire-pulse [installed]
                  pipewire
                  lib32-vulkan-icd-loader: Vulkan support [installed]
Required By     : None
    """)
    def test_map_optional_deps__no_remote_and_not_installed__several(self, run: Mock):
        res = pacman.map_optional_deps(('package-test',), remote=False, not_installed=True)
        run.assert_called_once_with(['pacman', '-Qi', 'package-test'])
        self.assertEqual({'package-test': {'pipewire-alsa': '', 'pipewire': ''}}, res)


class PacmanDatabasesTest(TestCase):
    """Repositorios declarados en pacman.conf (F34)."""

    def test_get_databases__recognizes_repositories_with_hyphen(self):
        dbs = pacman.get_databases(f'{FILE_DIR}/resources/pacman_chaotic.conf')

        self.assertEqual({'core-testing', 'core', 'extra', 'multilib', 'chaotic-aur', 'mi_repo-local'}, dbs)

    def test_get_databases__ignores_options_and_commented_sections(self):
        dbs = pacman.get_databases(f'{FILE_DIR}/resources/pacman_chaotic.conf')

        self.assertNotIn('options', dbs)
        self.assertNotIn('testing', dbs)

    def test_get_databases__manjaro_sample(self):
        dbs = pacman.get_databases(f'{FILE_DIR}/resources/pacman.conf')

        self.assertEqual({'core', 'extra', 'community', 'multilib'}, dbs)

    def test_get_databases__missing_file(self):
        self.assertEqual(set(), pacman.get_databases(f'{FILE_DIR}/resources/no_existe.conf'))


class PacmanNoShellTest(TestCase):
    """Los comandos se construyen como listas de argumentos, nunca como cadenas de shell (F36)."""

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value='')
    def test_search__passes_each_word_as_argument(self, run: Mock):
        pacman.search('firefox; touch /tmp/pwned')

        run.assert_called_once_with(['pacman', '-Ss', 'firefox;', 'touch', '/tmp/pwned'], print_error=False)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value='')
    def test_get_info__passes_the_name_as_argument(self, run: Mock):
        pacman.get_info('firefox`id`', remote=True)

        run.assert_called_once_with(['pacman', '-Si', 'firefox`id`'], print_error=False)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value='')
    def test_check_installed__passes_the_name_as_argument(self, run: Mock):
        pacman.check_installed('firefox && rm -rf /')

        run.assert_called_once_with(['pacman', '-Qq', 'firefox && rm -rf /'], print_error=False)

    @patch(f'{__package_name__}.gems.arch.pacman._run', return_value='core/zlib 1.3-1\n')
    def test_guess_repository__passes_the_name_as_argument(self, run: Mock):
        with patch(f'{__package_name__}.gems.arch.pacman.read_provides', return_value={'zlib'}):
            res = pacman.guess_repository('zlib>=1.2')

        run.assert_called_once_with(['pacman', '-Ss', 'zlib'])
        self.assertEqual(('zlib', 'core'), res)


class PacmanRepositoriesTest(TestCase):
    """Asociacion paquete -> repositorio (F76 y F16)."""

    @patch(f'{__package_name__}.gems.arch.pacman.guess_repository', return_value=None)
    @patch(f'{__package_name__}.gems.arch.pacman.new_subprocess')
    def test_get_repositories__does_not_match_by_substring(self, new_subprocess: Mock, guess_repository: Mock):
        proc = Mock()
        proc.stdout = [b'core/zlib 1.3-1\n',
                       b'    Compression library\n',
                       b'extra/zlib-ng 2.1-1\n',
                       b'    zlib replacement\n']
        new_subprocess.return_value = proc

        res = pacman.get_repositories(('zlib', 'zlib-ng'))

        self.assertEqual({'zlib': 'core', 'zlib-ng': 'extra'}, res)
        guess_repository.assert_not_called()

    @patch(f'{__package_name__}.gems.arch.pacman.guess_repository', return_value=None)
    @patch(f'{__package_name__}.gems.arch.pacman.new_subprocess')
    def test_get_repositories__only_the_longer_name_available(self, new_subprocess: Mock, guess_repository: Mock):
        proc = Mock()
        proc.stdout = [b'extra/zlib-ng 2.1-1\n', b'    zlib replacement\n']
        new_subprocess.return_value = proc

        res = pacman.get_repositories(('zlib', 'zlib-ng'))

        self.assertEqual({'zlib-ng': 'extra'}, res)
        guess_repository.assert_called_once_with('zlib')

    def test_get_repositories__no_names(self):
        self.assertEqual({}, pacman.get_repositories(()))

    def test_map_repositories_from_info(self):
        output = """Repository      : chaotic-aur
Name            : brave-bin
Version         : 1.60.114-1
Description     : Web browser

Repository      : extra
Name            : firefox
Version         : 121.0-1
Description     : Web browser
"""
        self.assertEqual({'brave-bin': 'chaotic-aur', 'firefox': 'extra'},
                         pacman.map_repositories_from_info(output))

    def test_map_repositories_from_info__no_output(self):
        self.assertEqual({}, pacman.map_repositories_from_info(None))
        self.assertEqual({}, pacman.map_repositories_from_info(''))

    @patch(f'{__package_name__}.gems.arch.pacman._run',
           return_value='Repository      : chaotic-aur\nName            : brave-bin\n')
    def test_map_available_repositories(self, run: Mock):
        res = pacman.map_available_repositories({'brave-bin', 'un-paquete-solo-del-aur'})

        run.assert_called_once_with(['pacman', '-Si', 'brave-bin', 'un-paquete-solo-del-aur'],
                                    print_error=False, ignore_return_code=True)
        self.assertEqual({'brave-bin': 'chaotic-aur'}, res)

    def test_map_available_repositories__no_names(self):
        self.assertEqual({}, pacman.map_available_repositories(set()))


class PacmanConflictingFilesTest(TestCase):
    """Rutas en conflicto para acotar --overwrite (F38)."""

    def test_list_conflicting_files__extracts_paths(self):
        output = """looking for conflicting files...
error: failed to commit transaction (conflicting files)
brave-bin: /usr/bin/brave exists in filesystem
brave-bin: /usr/share/applications/brave.desktop exists in filesystem
Errors occurred, no packages were upgraded.
"""
        self.assertEqual(['/usr/bin/brave', '/usr/share/applications/brave.desktop'],
                         pacman.list_conflicting_files(output))

    def test_list_conflicting_files__no_duplicates(self):
        output = ('pkg: /usr/bin/a exists in filesystem\n'
                  'otro: /usr/bin/a exists in filesystem\n')
        self.assertEqual(['/usr/bin/a'], pacman.list_conflicting_files(output))

    def test_list_conflicting_files__no_conflicts(self):
        self.assertEqual([], pacman.list_conflicting_files('todo correcto\n'))
        self.assertEqual([], pacman.list_conflicting_files(''))


class PacmanProcessBuildTest(TestCase):
    """Argumentos generados para pacman -U / -S / -R (F37 y F38)."""

    @staticmethod
    def _cmd(simple_process: Mock) -> list:
        return simple_process.call_args.kwargs['cmd']

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_install_as_process__repository_install_does_not_skip_dependency_checks(self, simple_process: Mock):
        pacman.install_as_process(pkgpaths=('brave-bin',), root_password=None, file=False)

        cmd = self._cmd(simple_process)
        self.assertEqual(['pacman', '-S', 'brave-bin', '--noconfirm'], cmd)
        self.assertNotIn('-dd', cmd)

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_install_as_process__file_install_keeps_dd(self, simple_process: Mock):
        pacman.install_as_process(pkgpaths=('/tmp/brave.pkg.tar.zst',), root_password=None, file=True)

        cmd = self._cmd(simple_process)
        self.assertEqual(['pacman', '-U', '/tmp/brave.pkg.tar.zst', '--noconfirm', '-dd'], cmd)

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_install_as_process__simulation_has_no_dd(self, simple_process: Mock):
        pacman.install_as_process(pkgpaths=('/tmp/brave.pkg.tar.zst',), root_password=None, file=True, simulate=True)

        cmd = self._cmd(simple_process)
        self.assertEqual(['pacman', '-U', '/tmp/brave.pkg.tar.zst', '--confirm'], cmd)

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_install_as_process__overwrite_only_the_detected_paths(self, simple_process: Mock):
        pacman.install_as_process(pkgpaths=('brave-bin',), root_password=None, file=False,
                                  overwrite_conflicting_files=True,
                                  conflicting_files=('/usr/bin/brave', '/usr/share/x.desktop'))

        cmd = self._cmd(simple_process)
        self.assertIn('--overwrite=/usr/bin/brave', cmd)
        self.assertIn('--overwrite=/usr/share/x.desktop', cmd)
        self.assertNotIn('--overwrite=*', cmd)

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_install_as_process__overwrite_falls_back_to_wildcard(self, simple_process: Mock):
        pacman.install_as_process(pkgpaths=('brave-bin',), root_password=None, file=False,
                                  overwrite_conflicting_files=True)

        self.assertIn('--overwrite=*', self._cmd(simple_process))

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_upgrade_several__overwrite_only_the_detected_paths(self, simple_process: Mock):
        pacman.upgrade_several(pkgnames=('brave-bin',), root_password=None,
                               overwrite_conflicting_files=True,
                               conflicting_files=('/usr/bin/brave',))

        cmd = self._cmd(simple_process)
        self.assertIn('--overwrite=/usr/bin/brave', cmd)
        self.assertNotIn('--overwrite=*', cmd)
        self.assertFalse(simple_process.call_args.kwargs['shell'])

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_remove_several__does_not_treat_warnings_as_success(self, simple_process: Mock):
        pacman.remove_several(pkgnames=('brave-bin',), root_password=None)

        kwargs = simple_process.call_args.kwargs
        self.assertEqual(['pacman', '-R', 'brave-bin', '--noconfirm'], kwargs['cmd'])
        self.assertNotIn('wrong_error_phrases', kwargs)
        self.assertIn('error: failed to prepare transaction', kwargs['error_phrases'])
        self.assertFalse(kwargs['shell'])

    @patch(f'{__package_name__}.gems.arch.pacman.SimpleProcess')
    def test_remove_several__skip_checks_adds_dd(self, simple_process: Mock):
        pacman.remove_several(pkgnames=('brave-bin',), root_password=None, skip_checks=True)

        self.assertIn('-dd', self._cmd(simple_process))


class PacmanRunningProcessTest(TestCase):
    """Deteccion de un pacman en ejecucion antes de borrar db.lck (F78)."""

    def test_list_running_pacman_pids__detects_the_process(self):
        with TemporaryDirectory() as proc_dir:
            for pid, comm in (('101', 'pacman'), ('202', 'firefox'), ('303', 'pacman')):
                os.mkdir(f'{proc_dir}/{pid}')
                with open(f'{proc_dir}/{pid}/comm', 'w') as f:
                    f.write(f'{comm}\n')

            os.mkdir(f'{proc_dir}/self')  # entradas no numericas se ignoran

            self.assertEqual({101, 303}, pacman.list_running_pacman_pids(proc_dir))

    def test_list_running_pacman_pids__none_running(self):
        with TemporaryDirectory() as proc_dir:
            os.mkdir(f'{proc_dir}/101')
            with open(f'{proc_dir}/101/comm', 'w') as f:
                f.write('bash\n')

            self.assertEqual(set(), pacman.list_running_pacman_pids(proc_dir))

    def test_list_running_pacman_pids__missing_proc_dir(self):
        self.assertEqual(set(), pacman.list_running_pacman_pids('/no/existe/proc'))
