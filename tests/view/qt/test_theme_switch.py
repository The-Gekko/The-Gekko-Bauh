import importlib.util
import logging
import os
import unittest

# los tests de interfaz deben poder ejecutarse sin servidor grafico
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

if PYQT5_AVAILABLE:
    from PyQt5.QtGui import QPalette
    from PyQt5.QtWidgets import QApplication, QTableWidget

    from bauh.context import set_theme
    from bauh.stylesheet import is_dark_color


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class ThemeSwitchTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.logger = logging.getLogger('test')
        self.config = {'ui': {'theme': 'aurora', 'system_theme': False}}
        self.table = QTableWidget(2, 2)
        self.table.show()

    def tearDown(self):
        self.table.deleteLater()
        self.app.setStyleSheet('')
        self.app.setPalette(self.app.style().standardPalette())

    def _apply(self, theme_key: str):
        self.config['ui']['theme'] = theme_key
        set_theme(theme_key=theme_key, app=self.app, logger=self.logger, app_config=self.config)
        self.app.processEvents()

    def _table_base(self) -> str:
        return self.table.palette().color(QPalette.Base).name()

    def test_switching_from_a_dark_theme_to_light_must_not_keep_the_dark_table(self):
        self._apply('aurora')
        self.assertTrue(is_dark_color(self._table_base()))

        self._apply('light')
        self.assertFalse(is_dark_color(self._table_base()), self._table_base())

    def test_switching_back_to_a_dark_theme_darkens_the_table_again(self):
        self._apply('light')
        self._apply('aurora')

        self.assertTrue(is_dark_color(self._table_base()), self._table_base())

    def test_an_unknown_theme_falls_back_to_aurora_instead_of_no_style(self):
        self._apply('darcula')

        self.assertIn('Aurora', self.app.styleSheet())
        self.assertTrue(is_dark_color(self._table_base()))
