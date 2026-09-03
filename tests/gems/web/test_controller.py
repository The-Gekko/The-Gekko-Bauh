from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from bauh import __package_name__
from bauh import __app_name__
from bauh.gems.web import PIPX_INJECT_COMMAND
from bauh.gems.web.controller import DEFAULT_LANGUAGE_HEADER
from bauh.gems.web.controller import WebApplicationManager
from bauh.gems.web.model import WebApplication


class ControllerTest(TestCase):

    def test_DEFAULT_LANGUAGE_HEADER(self):
        self.assertEqual('en-US, en', DEFAULT_LANGUAGE_HEADER)


class WebApplicationManagerTest(TestCase):

    def setUp(self):
        self.manager = WebApplicationManager(context=Mock())
        self.manager.i18n = {'web.missing_python_deps': 'missing: {deps} | fix: {cmd}'}

    def test_is_default_enabled__must_be_false_for_legacy_gems(self):
        self.assertFalse(self.manager.is_default_enabled())

    @patch(f'{__package_name__}.gems.web.controller.BS4_AVAILABLE', False)
    @patch(f'{__package_name__}.gems.web.controller.LXML_AVAILABLE', False)
    def test_can_work__must_report_missing_pypi_dependencies_with_a_pipx_hint(self):
        can_work, reason = self.manager.can_work()

        self.assertFalse(can_work)
        self.assertIn('beautifulsoup4', reason)
        self.assertIn('lxml', reason)
        self.assertIn(PIPX_INJECT_COMMAND, reason)
        # el nombre debe ser el de la distribucion instalable (pyproject/install.sh), porque el
        # usuario copia y pega el comando: con cualquier otro pipx responde «is not installed»
        self.assertIn(f'pipx inject {__app_name__}', reason)
        # no deben citarse paquetes de Debian: bajo pipx no sirven
        self.assertNotIn('python3-', reason)

    @patch(f'{__package_name__}.gems.web.controller.BS4_AVAILABLE', True)
    @patch(f'{__package_name__}.gems.web.controller.LXML_AVAILABLE', False)
    def test_can_work__must_only_report_the_dependencies_actually_missing(self):
        can_work, reason = self.manager.can_work()

        self.assertFalse(can_work)
        self.assertNotIn('beautifulsoup4', reason.split('|')[0])
        self.assertIn('lxml', reason.split('|')[0])

    @patch('locale.getdefaultlocale', side_effect=Exception)
    def test_get_accept_language_header__must_return_default_locale_when_exception_raised(self, getdefaultlocale: Mock):
        returned = self.manager.get_accept_language_header()
        self.assertEqual(DEFAULT_LANGUAGE_HEADER, returned)
        getdefaultlocale.assert_called_once()

    @patch('locale.getdefaultlocale', return_value=None)
    def test_get_accept_language_header__must_return_default_locale_when_no_locale_is_returned(self, getdefaultlocale: Mock):
        returned = self.manager.get_accept_language_header()
        self.assertEqual(DEFAULT_LANGUAGE_HEADER, returned)
        getdefaultlocale.assert_called_once()

    @patch('locale.getdefaultlocale', return_value=['es_AR'])
    def test_get_accept_language_header__must_return_the_system_locale_without_underscore_plus_default_locale(self, getdefaultlocale: Mock):
        returned = self.manager.get_accept_language_header()
        self.assertEqual(f'es-AR, es, {DEFAULT_LANGUAGE_HEADER}', returned)
        getdefaultlocale.assert_called_once()

    @patch('locale.getdefaultlocale', return_value=['es'])
    def test_get_accept_language_header__must_return_the_simple_system_locale_plus_default_locale(self, getdefaultlocale: Mock):
        returned = self.manager.get_accept_language_header()
        self.assertEqual(f'es, {DEFAULT_LANGUAGE_HEADER}', returned)
        getdefaultlocale.assert_called_once()

    @patch('locale.getdefaultlocale', return_value=['en_IN'])
    def test_get_accept_language_header__must_not_concatenate_default_locale_if_system_locale_has_it(self, getdefaultlocale: Mock):
        returned = self.manager.get_accept_language_header()
        self.assertEqual(f'en-IN, en', returned)
        getdefaultlocale.assert_called_once()

    def test_strip_url_protocol__http_no_www(self):
        res = self.manager.strip_url_protocol('http://test.com')
        self.assertEqual('test.com', res)

    def test_strip_url_protocol__http_with_www(self):
        res = self.manager.strip_url_protocol('http://www.test.com')
        self.assertEqual('test.com', res)

    def test_strip_url_protocol__https_no_www(self):
        res = self.manager.strip_url_protocol('https://test.com')
        self.assertEqual('test.com', res)

    def test_strip_url_protocol__https_with_www(self):
        res = self.manager.strip_url_protocol('https://www.test.com')
        self.assertEqual('test.com', res)


class DesktopEntryTest(TestCase):
    """Contenido del lanzador .desktop que se escribe al instalar una aplicación web."""

    def setUp(self):
        self.manager = WebApplicationManager.__new__(WebApplicationManager)

    @staticmethod
    def _pkg(name: str = 'Mi App', command: str = '/inst/mi-app/mi-app',
             categories=('Network',), package_name: str = 'mi-app', description: str = 'Una app'):
        pkg = MagicMock()
        pkg.name = name
        pkg.description = description
        pkg.url = 'https://ejemplo.test'
        pkg.categories = list(categories)
        pkg.package_name = package_name
        pkg.get_command.return_value = command
        pkg.get_disk_icon_path.return_value = '/inst/mi-app/icon.png'
        return pkg

    def _entry(self, **kwargs) -> dict:
        content = self.manager._gen_desktop_entry_content(self._pkg(**kwargs))
        self.assertTrue(content.startswith('[Desktop Entry]\n'),
                        'la especificación exige el grupo en la primera línea, sin sangría')
        return dict(line.split('=', 1) for line in content.strip().split('\n')[1:] if '=' in line)

    def test_a_path_with_spaces_is_quoted(self):
        # el directorio se construye con el nombre que elige el usuario: sin comillas, el
        # lanzador partía la ruta por el espacio y no arrancaba nada
        entry = self._entry(command='/inst/mi app/mi app')

        self.assertEqual('"/inst/mi app/mi app"', entry['Exec'])

    def test_a_plain_path_is_not_quoted(self):
        self.assertEqual('/inst/mi-app/mi-app', self._entry()['Exec'])

    def test_reserved_characters_are_escaped(self):
        entry = self._entry(command='/inst/a$b/`c`/app')

        self.assertEqual('"/inst/a\\$b/\\`c\\`/app"', entry['Exec'])

    def test_a_newline_in_the_description_does_not_break_the_file(self):
        # un salto de línea partiría el fichero y las claves siguientes se perderían
        entry = self._entry(description='Primera línea\nInyectada=si')

        self.assertEqual('Primera línea Inyectada=si', entry['Comment'])
        self.assertIn('Icon', entry)
        self.assertIn('Exec', entry)

    def test_the_categories_end_with_a_semicolon(self):
        # la especificación define Categories como una lista, y una lista termina en «;»
        entry = self._entry(categories=('Network', 'WebBrowser'))

        self.assertEqual('Network;WebBrowser;', entry['Categories'])

    def test_optional_keys_are_omitted_when_empty(self):
        content = self.manager._gen_desktop_entry_content(self._pkg(categories=(), package_name=None))

        self.assertNotIn('Categories', content)
        self.assertNotIn('StartupWMClass', content)
        # y no quedan líneas vacías donde antes iban esas claves
        self.assertNotIn('\n\n', content)


class LaunchCommandTest(TestCase):
    """La orden de lanzamiento se construye como lista, no como cadena de shell."""

    @staticmethod
    def _app(installation_dir: str = '/inst/mi app'):
        pkg = WebApplication(installation_dir=installation_dir)
        pkg.name = 'Mi App'
        return pkg

    def test_the_arguments_come_as_a_list(self):
        with patch(f'{__package_name__}.gems.web.model.user.is_root', return_value=False):
            args = self._app().get_command_args()

        self.assertEqual(1, len(args))
        self.assertNotIn('--no-sandbox', args)

    def test_root_adds_no_sandbox_as_its_own_argument(self):
        with patch(f'{__package_name__}.gems.web.model.user.is_root', return_value=True):
            args = self._app().get_command_args()

        # como argumento independiente, no pegado a la ruta dentro de una cadena
        self.assertEqual('--no-sandbox', args[-1])
        self.assertNotIn(' ', args[0].split('/')[-1] + '')

    def test_without_an_installation_dir_there_is_no_command(self):
        pkg = WebApplication()
        self.assertIsNone(pkg.get_command_args())
