"""La gem eopkg contra un binario ``eopkg`` simulado en el PATH.

Estas pruebas no parchean `_execute_eopkg`: dejan que la gem lance el proceso de verdad, con
lo que cubren a la vez los argumentos que construye y el análisis de la salida real que el
dueño del proyecto aportó. Un cambio en cualquiera de los dos extremos las rompe.
"""

import logging
import unittest
from unittest.mock import Mock, patch

from bauh import __package_name__
from bauh.gems.eopkg.controller import EopkgManager
from tests.integration.harness import FakeBinaries

# Salidas reales de Solus, recortadas.
LI_OUTPUT = """discord - All-in-one voice and text chat for gamers
vlc - The cross-platform open-source multimedia framework and player
"""

LI_INSTALL_INFO_OUTPUT = """discord 0.0.44 1 All-in-one voice and text chat for gamers
vlc 3.0.20 1 The cross-platform open-source multimedia framework and player
"""

SEARCH_OUTPUT = """vlc - The cross-platform open-source multimedia framework and player
vlc-devel - Development files for vlc
"""

LIST_UPGRADES_OUTPUT = """vlc
"""


def new_manager() -> EopkgManager:
    """EopkgManager con lo mínimo: el constructor real exige un ApplicationContext."""
    manager = EopkgManager.__new__(EopkgManager)
    logger = logging.getLogger('eopkg-integration')
    logger.addHandler(logging.NullHandler())

    manager.i18n = {}
    manager.logger = logger
    manager.configman = Mock()
    manager.configman.get_config.return_value = {'command_timeout': 30}
    manager._installed_index = None
    manager._upgradable_names = None
    return manager


class EopkgReadIntegrationTest(unittest.TestCase):
    """Lecturas: el binario se ejecuta de verdad y la gem interpreta su salida."""

    def setUp(self):
        self.manager = new_manager()

    def test_the_installed_index_comes_from_two_real_calls(self):
        responses = {'eopkg': {'li': {'stdout': LI_OUTPUT}}}

        with FakeBinaries(responses) as fakes:
            index = self.manager._read_installed_index()

            calls = fakes.calls('eopkg')

        self.assertEqual(2, len(calls))
        self.assertEqual(['li', '--no-color'], calls[0])
        self.assertEqual(['li', '--no-color', '--install-info'], calls[1])
        self.assertEqual({'discord', 'vlc'}, set(index))

    def test_the_install_info_output_fills_in_the_versions(self):
        # el binario responde distinto a 'li' según lleve o no --install-info, que es lo que
        # hace el eopkg real: el resumen en una llamada, la versión en la otra
        responses = {'eopkg': {'li': {'stdout': LI_INSTALL_INFO_OUTPUT}}}

        with FakeBinaries(responses):
            index = self.manager._read_installed_index()

        self.assertEqual('3.0.20', index['vlc']['version'])
        self.assertEqual('1', index['vlc']['release'])

    def test_a_failing_binary_leaves_no_cached_index(self):
        responses = {'eopkg': {'li': {'stdout': '', 'stderr': 'database is locked', 'code': 1}}}

        with FakeBinaries(responses):
            self.assertEqual({}, self.manager._read_installed_index())

        self.assertIsNone(self.manager._installed_index)

    def test_the_upgradable_list_comes_from_list_upgrades(self):
        responses = {'eopkg': {'list-upgrades': {'stdout': LIST_UPGRADES_OUTPUT}}}

        with FakeBinaries(responses) as fakes:
            upgradable = self.manager._read_upgradable()
            called = fakes.was_called_with('eopkg', ['list-upgrades', '--no-color'])

        self.assertEqual(['vlc'], upgradable)
        self.assertTrue(called)

    def test_every_read_forces_a_neutral_locale(self):
        # sin LANG/LC_ALL fijos, un Solus en español devuelve «Instalado 1 / 4» y los
        # analizadores, escritos contra la salida inglesa, dejan de reconocer nada
        responses = {'eopkg': {'li': {'stdout': LI_OUTPUT}}}

        with FakeBinaries(responses), patch.dict('os.environ', {'LANG': 'es_ES.UTF-8'}):
            with patch(f'{__package_name__}.gems.eopkg.controller.subprocess.run') as run:
                run.return_value = Mock(returncode=0, stdout='', stderr='')
                self.manager._read_installed_index()

        env = run.call_args.kwargs['env']
        self.assertEqual('C.UTF-8', env['LANG'])
        self.assertEqual('C.UTF-8', env['LC_ALL'])


class EopkgSearchIntegrationTest(unittest.TestCase):
    """Búsqueda: la gem distingue instalado de nuevo con lo que devuelve el binario."""

    def setUp(self):
        self.manager = new_manager()

    def test_search_marks_the_installed_package(self):
        responses = {'eopkg': {'sr': {'stdout': SEARCH_OUTPUT},
                               'li': {'stdout': LI_INSTALL_INFO_OUTPUT},
                               'list-upgrades': {'stdout': ''}}}

        with FakeBinaries(responses) as fakes:
            res = self.manager.search(words='vlc', disk_loader=None)

            search_calls = [c for c in fakes.calls('eopkg') if c and c[0] == 'sr']

        self.assertEqual([['sr', '--no-color', 'vlc']], search_calls)
        self.assertEqual({'vlc'}, {p.name for p in res.installed})
        self.assertEqual({'vlc-devel'}, {p.name for p in res.new})

    def test_a_failing_search_does_not_crash(self):
        responses = {'eopkg': {'sr': {'stdout': '', 'stderr': 'network error', 'code': 1},
                               'li': {'stdout': LI_OUTPUT},
                               'list-upgrades': {'stdout': ''}}}

        with FakeBinaries(responses):
            res = self.manager.search(words='vlc', disk_loader=None)

        self.assertEqual([], res.new)
        self.assertEqual([], res.installed)


if __name__ == '__main__':
    unittest.main()
