import os
import subprocess
import sys
import tempfile
import unittest

import bauh

# Raíz del repositorio: dos niveles por encima de tests/installer/.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:  # tomllib entra en la biblioteca estándar en Python 3.11
    import tomllib
except ImportError:  # pragma: no cover - solo en 3.8-3.10
    tomllib = None


def read_pyproject() -> dict:
    with open(os.path.join(REPO_ROOT, 'pyproject.toml'), 'rb') as file_handle:
        return tomllib.load(file_handle)


def read_desktop(name: str) -> dict:
    """Lee un .desktop como pares clave=valor (basta para lo que se comprueba)."""
    entries = {}

    with open(os.path.join(REPO_ROOT, 'bauh', 'desktop', name), 'r', encoding='utf-8') as file_handle:
        for line in file_handle:
            stripped = line.strip()

            if not stripped or stripped.startswith('#') or stripped.startswith('['):
                continue

            key, _, value = stripped.partition('=')
            entries[key.strip()] = value.strip()

    return entries


class VersionMetadataTest(unittest.TestCase):
    """La versión y las URLs del fork (F103)."""

    def test_version_uses_the_fork_local_scheme(self):
        self.assertEqual('0.10.8+gekko.1', bauh.__version__)

    def test_version_matches_the_agreed_pattern(self):
        # <base upstream>+gekko.<n>: distingue el fork de la 0.10.8 del upstream.
        self.assertRegex(bauh.__version__, r'^\d+\.\d+\.\d+\+gekko\.\d+$')

    def test_app_name_is_unchanged(self):
        # El identificador técnico manda en rutas de configuración y binarios:
        # cambiarlo movería ~/.config/bauh y rompería instalaciones existentes.
        self.assertEqual('bauh', bauh.__app_name__)

    def test_display_name(self):
        self.assertEqual('bauh Gekko Edition', bauh.__display_name__)

    def test_repo_urls(self):
        self.assertEqual('https://github.com/The-Gekko/Bauh-Fork-The-Gekko', bauh.__repo_url__)
        self.assertEqual('https://github.com/vinifmor/bauh', bauh.__upstream_url__)

    def test_version_is_a_literal_on_the_first_line(self):
        # setuptools lee la versión con `attr: bauh.__version__` mediante análisis
        # estático, e install.sh y la documentación asumen que está en la línea 1.
        with open(os.path.join(REPO_ROOT, 'bauh', '__init__.py'), 'r', encoding='utf-8') as file_handle:
            first_line = file_handle.readline().rstrip('\n')

        self.assertRegex(first_line, r"^__version__ = '[^']+'$")
        self.assertIn(bauh.__version__, first_line)


@unittest.skipUnless(tomllib is not None, 'tomllib requiere Python 3.11+')
class PyprojectTest(unittest.TestCase):
    """La tabla [project] restaurada (F17, F52, F90)."""

    @classmethod
    def setUpClass(cls):
        cls.pyproject = read_pyproject()
        cls.project = cls.pyproject['project']

    def test_distribution_name_is_the_fork_one(self):
        # bauh-gekko no colisiona con el «bauh» de PyPI/AUR.
        self.assertEqual('bauh-gekko', self.project['name'])

    def test_version_is_dynamic_and_read_from_the_package(self):
        self.assertEqual(['version'], self.project['dynamic'])
        dynamic = self.pyproject['tool']['setuptools']['dynamic']
        self.assertEqual({'attr': 'bauh.__version__'}, dynamic['version'])

    def test_authors_and_maintainers(self):
        authors = {author['name'] for author in self.project['authors']}
        maintainers = {maintainer['name'] for maintainer in self.project['maintainers']}
        self.assertIn('Vinicius Moreira', authors)
        self.assertIn('The-Gekko', maintainers)

    def test_readme_and_python_requirement(self):
        self.assertEqual('README.md', self.project['readme'])
        self.assertEqual('>=3.8', self.project['requires-python'])

    def test_license_is_zlib(self):
        classifiers = self.project['classifiers']
        self.assertIn('License :: OSI Approved :: zlib/libpng License', classifiers)
        self.assertEqual(['LICENSE'], self.pyproject['tool']['setuptools']['license-files'])

    def test_classifiers_cover_python_38_to_314(self):
        classifiers = set(self.project['classifiers'])
        for minor in range(8, 15):
            self.assertIn(f'Programming Language :: Python :: 3.{minor}', classifiers)

    def test_console_scripts(self):
        self.assertEqual({'bauh': 'bauh.app:main',
                          'bauh-tray': 'bauh.app:tray',
                          'bauh-cli': 'bauh.cli.app:main'},
                         self.project['scripts'])

    def test_optional_dependencies(self):
        optional = self.project['optional-dependencies']
        self.assertIn('web', optional)
        self.assertIn('test', optional)
        web = ' '.join(optional['web'])
        self.assertIn('lxml', web)
        self.assertIn('beautifulsoup4', web)

    def test_urls_point_to_the_fork_and_credit_upstream(self):
        urls = self.project['urls']
        self.assertEqual(bauh.__repo_url__, urls['Homepage'])
        self.assertEqual(bauh.__upstream_url__, urls['Upstream'])

    def test_package_data_ships_resources(self):
        package_data = self.pyproject['tool']['setuptools']['package-data']['bauh']
        for pattern in ('view/resources/locale/*',
                        'view/resources/img/*',
                        'view/resources/style/*',
                        'gems/*/resources/locale/*',
                        'desktop/*'):
            self.assertIn(pattern, package_data)

    def test_dependencies_match_requirements_txt(self):
        # requirements.txt e install.sh se apoyan en las mismas cotas: si divergen,
        # el entorno de pipx y el wheel dejan de instalar lo mismo (F137).
        with open(os.path.join(REPO_ROOT, 'requirements.txt'), 'r', encoding='utf-8') as file_handle:
            requirements = [line.strip() for line in file_handle
                            if line.strip() and not line.startswith('#')]

        self.assertEqual(sorted(requirements), sorted(self.project['dependencies']))

    def test_requirements_declare_a_lower_and_upper_bound(self):
        for requirement in self.project['dependencies']:
            self.assertRegex(requirement, r'>=\d', f'{requirement} no fija una versión mínima')
            self.assertIn('<', requirement, f'{requirement} no fija techo de major')

    def test_setup_py_and_cfg_are_gone(self):
        # Quedaron cubiertos por [project]; conservarlos duplicaría metadatos.
        self.assertFalse(os.path.exists(os.path.join(REPO_ROOT, 'setup.py')))
        self.assertFalse(os.path.exists(os.path.join(REPO_ROOT, 'setup.cfg')))


class DesktopEntriesTest(unittest.TestCase):
    """Las plantillas .desktop del fork (F64, F121, F129)."""

    def test_main_entry(self):
        entry = read_desktop('bauh.desktop')
        self.assertEqual('bauh Gekko Edition', entry['Name'])
        self.assertEqual('Application', entry['Type'])
        # StartupWMClass permite a Wayland/KDE asociar la ventana al lanzador.
        self.assertEqual('bauh', entry['StartupWMClass'])
        self.assertIn('Name[es]', entry)
        self.assertIn('Comment[es]', entry)
        self.assertIn('Keywords', entry)

    def test_tray_entry_exists_and_targets_the_tray_binary(self):
        entry = read_desktop('bauh_tray.desktop')
        self.assertIn('bauh-tray', entry['Exec'])
        self.assertIn('Name[es]', entry)
        self.assertIn('Comment[es]', entry)
        self.assertEqual('bauh', entry['StartupWMClass'])

    def test_icon_name_does_not_collide_with_the_official_package(self):
        # Con Icon=bauh, el icono del fork sustituiría al del bauh oficial en
        # cuanto ambos convivieran (QIcon.fromTheme('bauh')).
        for name in ('bauh.desktop', 'bauh_tray.desktop'):
            self.assertEqual('bauh-gekko', read_desktop(name)['Icon'], name)

    def test_scope_is_described_in_both_entries(self):
        for name in ('bauh.desktop', 'bauh_tray.desktop'):
            comment = read_desktop(name)['Comment']
            for technology in ('Arch/AUR', 'Chaotic AUR', 'Flatpak', 'eopkg'):
                self.assertIn(technology, comment, f'{name}: falta «{technology}»')


class InstallScriptTest(unittest.TestCase):
    """Invariantes del instalador que otros ficheros dan por supuestas."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO_ROOT, 'install.sh'), 'r', encoding='utf-8') as file_handle:
            cls.source = file_handle.read()

    def test_passes_the_chosen_interpreter_to_pipx(self):
        # Sin --python, pipx usa su intérprete por defecto y el mensaje
        # «Instalando con python3.12» miente (F136).
        self.assertIn('--python "$PYTHON_BIN"', self.source)

    def test_downloads_the_resolved_commit_not_a_branch_zip(self):
        # Descargar heads/master.zip después de consultar el SHA abre una ventana
        # en la que la marca guardada no corresponde a lo instalado (F04).
        self.assertNotIn('heads/master.zip', self.source)
        self.assertIn('$ARCHIVE_BASE/$resolved_ref.zip', self.source)

    def test_aborts_when_the_reference_cannot_be_resolved(self):
        self.assertIn('No se pudo resolver', self.source)
        self.assertIn('^[0-9a-f]{40}$', self.source)

    def test_supports_a_ref_option(self):
        self.assertIn('--ref', self.source)
        self.assertIn('REQUESTED_REF', self.source)

    def test_privileged_actions_need_explicit_flags(self):
        # --yes no debe autorizar sudo (F51).
        self.assertIn('--remove-system-bauh', self.source)
        self.assertIn('--install-pipx', self.source)
        self.assertIn('sudo -n true', self.source)

    def test_does_not_use_eval(self):
        self.assertNotRegex(self.source, r'(?m)^\s*eval\s')

    def test_uses_the_fork_package_name(self):
        self.assertIn('PKG_NAME="bauh-gekko"', self.source)

    def test_does_not_shadow_the_official_launcher(self):
        # Escribir ~/.local/share/applications/bauh.desktop taparía por
        # precedencia XDG al lanzador del paquete oficial (F129).
        self.assertIn('DESKTOP_ID="bauh-gekko"', self.source)
        self.assertIn('ICON_NAME="bauh-gekko"', self.source)

    def test_purges_cache_share_and_temp(self):
        # F127: --purge prometía una limpieza que no hacía.
        for path in ('$HOME/.config/bauh',
                     '$HOME/.cache/bauh',
                     '$HOME/.local/share/bauh',
                     '/tmp/bauh@$user_name'):
            self.assertIn(path, self.source)

    def test_purge_also_covers_the_xdg_variants(self):
        # Según la versión instalada, bauh usa las rutas fijas o las XDG.
        for variable in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR'):
            self.assertIn(variable, self.source)

    def test_offers_to_reset_a_fork_only_theme(self):
        # F123: volver al bauh oficial con ui.theme=aurora deja la UI sin estilos.
        self.assertIn('aurora|matugen|gtk', self.source)

    def test_installs_every_hicolor_size(self):
        self.assertIn('ICON_SIZES=(16 32 48 64 128 256 512)', self.source)
        self.assertIn('gekko-bauh-$size.png', self.source)


class CheckLocalesToolTest(unittest.TestCase):
    """La herramienta de paridad de traducciones usada por el job de CI."""

    TOOL = os.path.join(REPO_ROOT, 'tools', 'check_locales.py')

    def build_tree(self, root: str, languages: dict):
        locale_dir = os.path.join(root, 'bauh', 'view', 'resources', 'locale')
        os.makedirs(locale_dir)

        for language, keys in languages.items():
            with open(os.path.join(locale_dir, language), 'w', encoding='utf-8') as file_handle:
                for key, value in keys.items():
                    file_handle.write(f'{key}={value}\n')

    def run_tool(self, root: str, *args):
        return subprocess.run([sys.executable, self.TOOL, '--root', root, *args],
                              capture_output=True, text=True)

    def test_passes_when_every_language_is_complete(self):
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A', 'b': 'B'},
                                   'es': {'a': 'A', 'b': 'B'}})
            result = self.run_tool(root)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_fails_and_names_the_missing_key(self):
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A', 'b': 'B'},
                                   'es': {'a': 'A'}})
            result = self.run_tool(root)

        self.assertEqual(1, result.returncode)
        self.assertIn('b', result.stdout)
        self.assertIn('es', result.stdout)

    def test_report_mode_never_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A', 'b': 'B'},
                                   'es': {'a': 'A'}})
            result = self.run_tool(root, '--report')

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_languages_option_limits_what_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A', 'b': 'B'},
                                   'es': {'a': 'A', 'b': 'B'},
                                   'it': {'a': 'A'}})
            limited = self.run_tool(root, '--languages', 'es')
            everything = self.run_tool(root)

        self.assertEqual(0, limited.returncode, limited.stdout)
        self.assertEqual(1, everything.returncode, everything.stdout)

    def test_malformed_line_is_an_error(self):
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A'}, 'es': {'a': 'A'}})
            locale_dir = os.path.join(root, 'bauh', 'view', 'resources', 'locale')
            with open(os.path.join(locale_dir, 'es'), 'a', encoding='utf-8') as file_handle:
                file_handle.write('linea sin igual\n')
            result = self.run_tool(root)

        self.assertEqual(1, result.returncode)
        self.assertIn('sin «=»', result.stdout)

    def test_finds_nested_locale_sets(self):
        # locale/about y locale/tray se cargan por separado y es fácil olvidarlos.
        with tempfile.TemporaryDirectory() as root:
            self.build_tree(root, {'en': {'a': 'A'}, 'es': {'a': 'A'}})
            about_dir = os.path.join(root, 'bauh', 'view', 'resources', 'locale', 'about')
            os.makedirs(about_dir)
            with open(os.path.join(about_dir, 'en'), 'w', encoding='utf-8') as file_handle:
                file_handle.write('about.title=Title\n')
            with open(os.path.join(about_dir, 'es'), 'w', encoding='utf-8') as file_handle:
                file_handle.write('\n')
            result = self.run_tool(root)

        self.assertEqual(1, result.returncode)
        self.assertIn('about.title', result.stdout)


class RealLocaleFilesTest(unittest.TestCase):
    """Los locales reales del repositorio no deben tener líneas mal formadas."""

    def test_no_malformed_lines_in_shipped_locales(self):
        result = subprocess.run([sys.executable,
                                 os.path.join(REPO_ROOT, 'tools', 'check_locales.py'),
                                 '--root', REPO_ROOT, '--report'],
                                capture_output=True, text=True)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        errors = [line for line in result.stdout.splitlines() if line.startswith('ERROR')]
        self.assertEqual([], errors)


if __name__ == '__main__':
    unittest.main()
