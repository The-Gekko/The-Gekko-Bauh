import importlib.util
import unittest
from unittest.mock import MagicMock

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

if PYQT5_AVAILABLE:
    from bauh.view.qt.commons import PackageFilters, is_package_hidden


def _filters(name):
    return PackageFilters(category='any', display_limit=0, name=name, only_apps=False, only_verified=False,
                          only_updates=False, only_installed=False, search=None, type='any')


def _pkg(name):
    pkg = MagicMock()
    pkg.model.name = name
    return pkg


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class NameFilterTest(unittest.TestCase):
    """El nombre tiene que contener lo escrito, igual que en el índice de la tabla."""

    def test_a_package_containing_the_text_is_shown(self):
        for typed in ('fire', 'FOX', 'refo', '  firefox '):
            self.assertFalse(is_package_hidden(_pkg('firefox'), _filters(typed)), typed)

    def test_a_package_not_containing_the_text_is_hidden(self):
        self.assertTrue(is_package_hidden(_pkg('firefox'), _filters('chrome')))

    def test_the_old_reversed_check_is_gone(self):
        # antes se comprobaba al revés (si lo escrito empezaba por el nombre del paquete):
        # 'fire' ocultaba 'firefox' y 'firefox-bin' lo dejaba a la vista
        self.assertFalse(is_package_hidden(_pkg('firefox'), _filters('fire')))
        self.assertTrue(is_package_hidden(_pkg('firefox'), _filters('firefox-bin')))
