"""La gem Flatpak contra un binario `flatpak` simulado en el PATH.

Flatpak está activa por defecto, así que su buscador es una de las pocas entradas de texto
libre que llegan directamente a un comando. Estas pruebas ejecutan el proceso de verdad: si
alguien volviera a construir la orden interpolando en una cadena de shell, fallarían.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from bauh.gems.flatpak import flatpak
from tests.integration.harness import FakeBinaries

REMOTES_OUTPUT = "flathub\thttps://dl.flathub.org/repo/\n"

SEARCH_OUTPUT = (
    "Firefox\tWeb browser\torg.mozilla.firefox\t121.0\tstable\tflathub\n"
    "Chromium\tWeb browser\torg.chromium.Chromium\t120.0\tstable\tflathub\n"
)

INFO_OUTPUT = """       ID: org.mozilla.firefox
      Ref: app/org.mozilla.firefox/x86_64/stable
     Arch: x86_64
   Branch: stable
  Version: 121.0
   Commit: 0123456789abcdef
"""


class FlatpakNoShellIntegrationTest(unittest.TestCase):
    """El texto del usuario nunca se interpreta como una orden."""

    def setUp(self):
        self.marker = os.path.join(tempfile.mkdtemp(prefix='gekko-flatpak-'), 'ejecutado')

    def test_a_search_term_with_a_semicolon_is_not_executed(self):
        # con la construcción anterior («flatpak search {word} --user» en una cadena de shell)
        # este término creaba el fichero: el shell partía la orden en dos
        word = f'firefox; touch {self.marker} #'

        with FakeBinaries({'flatpak': {'*': {'stdout': ''}}}) as fakes:
            flatpak.search(version=('1', '14'), word=word, installation='user')
            calls = fakes.calls('flatpak')

        self.assertFalse(os.path.exists(self.marker), 'el buscador ejecutó una orden arbitraria')
        self.assertEqual([['search', word, '--user']], calls)

    def test_an_app_id_with_backticks_is_not_executed(self):
        app_id = f'org.mozilla.firefox`touch {self.marker}`'

        with FakeBinaries({'flatpak': {'*': {'stdout': ''}}}) as fakes:
            flatpak.get_app_info(app_id=app_id, branch='stable', installation='user')
            calls = fakes.calls('flatpak')

        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual([['info', app_id, 'stable', '--user']], calls)

    def test_a_remote_origin_with_metacharacters_is_not_executed(self):
        # el origen y la referencia vienen de los metadatos de un remoto, es decir, de un tercero
        origin = f'flathub; touch {self.marker} #'

        with FakeBinaries({'flatpak': {'*': {'stdout': INFO_OUTPUT}}}) as fakes:
            flatpak.get_app_commits_data(app_ref='app/org.mozilla.firefox/x86_64/stable',
                                         origin=origin, installation='user')
            calls = fakes.calls('flatpak')

        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual([['remote-info', '--log', origin,
                           'app/org.mozilla.firefox/x86_64/stable', '--user']], calls)


class FlatpakOutputIntegrationTest(unittest.TestCase):
    """Lo que la gem entiende de la salida real del binario."""

    def test_search_reads_the_columns_of_the_real_output(self):
        with FakeBinaries({'flatpak': {'*': {'stdout': SEARCH_OUTPUT}}}):
            found = flatpak.search(version=('1', '14'), word='browser', installation='user')

        self.assertEqual(2, len(found))
        self.assertEqual('org.mozilla.firefox', found[0]['id'])
        self.assertEqual('flathub', found[0]['origin'])

    def test_has_remotes_set_reads_the_remote_list(self):
        with FakeBinaries({'flatpak': {'*': {'stdout': REMOTES_OUTPUT}}}):
            self.assertTrue(flatpak.has_remotes_set())

        with FakeBinaries({'flatpak': {'*': {'stdout': ''}}}):
            self.assertFalse(flatpak.has_remotes_set())

    def test_a_failing_binary_does_not_raise(self):
        with FakeBinaries({'flatpak': {'*': {'stdout': '', 'stderr': 'error', 'code': 1}}}):
            self.assertIsNone(flatpak.get_version())


class FlatpakLanguagesIntegrationTest(unittest.TestCase):
    """Con la locale C flatpak no ve ningún idioma y pide las traducciones de todos.

    Fallo real: tres «Locale» en la lista de actualizaciones que no se iban nunca.  Cada
    '.Locale' instalada sólo con '/es' salía como pendiente al consultar con la locale C, el
    'flatpak update' de la actualización (con la locale real) no hacía nada, y vuelta a empezar.
    """

    def test_the_update_query_must_carry_the_user_languages(self):
        with patch.dict(os.environ, {'LANG': 'es_MX.utf8'}, clear=False), \
                FakeBinaries({'flatpak': {'*': {'stdout': 'Nothing to update.\n'}}}) as fakes:
            os.environ.pop('LANGUAGE', None)
            os.environ.pop('LC_ALL', None)
            os.environ.pop('LC_MESSAGES', None)
            flatpak.list_updates_as_str(('1', '18', '3'))
            envs = fakes.envs('flatpak')

        self.assertEqual(2, len(envs))  # instalación de sistema y de usuario

        for env in envs:
            # la salida sigue en inglés para poder analizarla (gettext ignora LANGUAGE con C)...
            self.assertEqual('C', env['LC_ALL'])
            # ...pero flatpak calcula los idiomas a partir de LANGUAGE (glib)
            self.assertEqual('es_MX.utf8', env['LANGUAGE'])

    def test_hidden_installed_refs_are_listed(self):
        output = ('io.missioncenter.MissionCenter\tstable\tuser\n'
                  'io.missioncenter.MissionCenter.Locale\tstable\tuser\n'
                  'org.gnome.Platform.Locale\t49\tsystem\n')

        with FakeBinaries({'flatpak': {'list': {'stdout': output}}}) as fakes:
            refs = flatpak.list_installed_refs()
            calls = fakes.calls('flatpak')

        self.assertIn(('io.missioncenter.MissionCenter.Locale', 'stable', 'user'), refs)
        self.assertIn(('org.gnome.Platform.Locale', '49', 'system'), refs)
        self.assertEqual([['list', '--all', '--columns=application,branch,installation']], calls)


if __name__ == '__main__':
    unittest.main()


class FlatpakProcessReapingTest(unittest.TestCase):
    """Las consultas no dejan procesos zombi."""

    LIST_OUTPUT = (
        "org.mozilla.firefox\tapp/org.mozilla.firefox/x86_64/stable\tx86_64\tstable"
        "\tWeb browser\tflathub\tsystem\tFirefox\t121.0\n"
    )

    @staticmethod
    def _own_zombies() -> int:
        count = 0

        for entry in os.listdir('/proc'):
            if not entry.isdigit():
                continue

            try:
                with open(f'/proc/{entry}/stat') as f:
                    fields = f.read().rsplit(')', 1)[1].split()
            except OSError:
                continue

            if fields and fields[0] == 'Z' and int(fields[1]) == os.getpid():
                count += 1

        return count

    def test_listing_installed_apps_leaves_no_zombies(self):
        before = self._own_zombies()

        with FakeBinaries({'flatpak': {'*': {'stdout': self.LIST_OUTPUT}}}):
            for _ in range(15):
                installed = flatpak.list_installed(('1', '14'))

        self.assertEqual(1, len(installed))
        self.assertEqual('org.mozilla.firefox', installed[0]['id'])
        self.assertEqual(before, self._own_zombies())

    def test_reading_fields_uses_a_single_process(self):
        info = 'ID: org.mozilla.firefox\nVersion: 121.0\nArch: x86_64\n'

        with FakeBinaries({'flatpak': {'*': {'stdout': info}}}) as fakes:
            fields = flatpak.get_fields('org.mozilla.firefox', 'stable', ['ID', 'Version'])
            calls = fakes.calls()

        self.assertEqual(['org.mozilla.firefox', '121.0'], fields)
        # antes se encadenaba un «grep» por una tubería: dos procesos, ninguno recogido
        self.assertEqual([['info', 'org.mozilla.firefox', 'stable']], calls)
