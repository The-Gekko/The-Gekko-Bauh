import logging
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh import __package_name__
from bauh.gems.eopkg.controller import EopkgManager

CONTROLLER = f'{__package_name__}.gems.eopkg.controller'

LI_OUTPUT = """discord - All-in-one voice and text chat
vlc - VLC media player
"""

LI_INSTALL_INFO_OUTPUT = """discord 0.0.44 1 All-in-one voice and text chat
vlc 3.0.20 1 VLC media player
"""


def new_manager() -> EopkgManager:
    """Instancia mínima de EopkgManager: el constructor real exige un ApplicationContext."""
    manager = EopkgManager.__new__(EopkgManager)
    logger = logging.getLogger('eopkg-tests')
    logger.addHandler(logging.NullHandler())

    manager.i18n = {}
    manager.logger = logger
    manager.configman = Mock()
    manager.configman.get_config.return_value = {'command_timeout': 60}
    manager._installed_index = None
    manager._upgradable_names = None
    return manager


class ReadInstalledIndexTest(TestCase):
    """Índice de paquetes instalados y su caché de sesión."""

    def setUp(self):
        self.manager = new_manager()

    def test_the_index_joins_the_summary_and_the_version(self):
        outputs = [(True, LI_OUTPUT), (True, LI_INSTALL_INFO_OUTPUT)]

        with patch.object(EopkgManager, '_execute_eopkg', side_effect=outputs):
            index = self.manager._read_installed_index()

        self.assertEqual({'discord', 'vlc'}, set(index))
        self.assertEqual('0.0.44', index['discord']['version'])
        self.assertEqual('1', index['discord']['release'])
        self.assertEqual('All-in-one voice and text chat', index['discord']['summary'])

    def test_a_failed_read_is_not_cached(self):
        # con la base de datos bloqueada por un «sudo eopkg up» en un terminal, cachear el
        # índice vacío dejaba toda búsqueda diciendo «no instalado» el resto de la sesión
        failures = [(False, ''), (False, '')]

        with patch.object(EopkgManager, '_execute_eopkg', side_effect=failures):
            self.assertEqual({}, self.manager._read_installed_index())

        self.assertIsNone(self.manager._installed_index)

        outputs = [(True, LI_OUTPUT), (True, LI_INSTALL_INFO_OUTPUT)]

        with patch.object(EopkgManager, '_execute_eopkg', side_effect=outputs):
            self.assertEqual({'discord', 'vlc'}, set(self.manager._read_installed_index()))

    def test_a_partial_read_is_cached(self):
        outputs = [(True, LI_OUTPUT), (False, '')]

        with patch.object(EopkgManager, '_execute_eopkg', side_effect=outputs):
            index = self.manager._read_installed_index()

        self.assertEqual({'discord', 'vlc'}, set(index))
        self.assertIsNotNone(self.manager._installed_index)

    def test_the_index_is_cached_between_calls(self):
        outputs = [(True, LI_OUTPUT), (True, LI_INSTALL_INFO_OUTPUT)]

        with patch.object(EopkgManager, '_execute_eopkg', side_effect=outputs) as execute:
            self.manager._read_installed_index()
            self.manager._read_installed_index()

        self.assertEqual(2, execute.call_count)
