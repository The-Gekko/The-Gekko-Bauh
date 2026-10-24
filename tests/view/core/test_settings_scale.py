import importlib.util
import unittest
from unittest import TestCase

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class ScaleSettingTest(TestCase):
    """«Escala» sustituye a HDPI + autoescala + factor, que se pisaban entre sí."""

    def _manager(self):
        from bauh.view.core.settings import GenericSettingsManager
        from bauh.view.util.translation import I18n

        manager = object.__new__(GenericSettingsManager)
        manager.i18n = I18n('en', {}, 'en', {})
        return manager

    def _select(self, auto_scale: bool, factor):
        return self._manager()._gen_scale_select({'ui': {'auto_scale': auto_scale, 'scale_factor': factor}})

    def test_automatic_is_the_selected_option_when_auto_scale_is_on(self):
        select = self._select(True, 1.0)

        self.assertEqual('auto', select.get_selected())
        self.assertEqual(['auto', '1', '1.25', '1.5', '1.75', '2'], [o.value for o in select.options])

    def test_a_fixed_factor_is_selected(self):
        self.assertEqual('1.5', self._select(False, 1.5).get_selected())

    def test_a_custom_factor_from_before_is_kept_as_an_option(self):
        select = self._select(False, 1.1)

        self.assertEqual('1.1', select.get_selected())
        self.assertIn('110 %', [o.label for o in select.options])

    def test_an_invalid_or_tiny_factor_falls_back_to_100(self):
        self.assertEqual('1', self._select(False, 'abc').get_selected())
        self.assertEqual('1', self._select(False, 0.5).get_selected())

    def test_the_select_can_be_drawn_as_a_qt_widget(self):
        # new_select deja max_width en None si no se le pasa, y el desplegable de Qt lo compara
        # con un número: así Ajustes dejaba de abrirse
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt5.QtWidgets import QApplication
        from bauh.view.qt.components import to_widget

        app = QApplication.instance() or QApplication([])  # sin guardarla, Python la libera al instante
        select = self._select(True, 1.0)

        self.assertEqual(-1, select.max_width)
        self.assertIsNotNone(to_widget(select, self._manager().i18n))
        self.assertIsNotNone(app)

    def test_the_interface_tab_has_a_single_scale_option(self):
        import inspect
        from bauh.view.core.settings import GenericSettingsManager

        source = inspect.getsource(GenericSettingsManager._gen_interface_settings)
        for retired in ("'hdpi'", "'auto_scale'", "'scalef'"):
            self.assertNotIn(retired, source)
