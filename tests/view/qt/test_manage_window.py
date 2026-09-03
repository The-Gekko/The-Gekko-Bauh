import importlib.util
import logging
import os
import unittest
from unittest.mock import MagicMock, patch

# los tests de interfaz deben poder ejecutarse sin servidor grafico
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

if PYQT5_AVAILABLE:
    from PyQt5.QtGui import QCloseEvent, QIcon
    from PyQt5.QtWidgets import QApplication, QSizePolicy

    from bauh.api.abstract.cache import MemoryCache
    from bauh.api.abstract.context import ApplicationContext
    from bauh.api.abstract.controller import SoftwareManager
    from bauh.api.abstract.model import PackageStatus, SoftwarePackage
    from bauh.api.abstract.view import SpacerComponent
    from bauh.api.http import HttpClient
    from bauh.view.qt.components import new_spacer, to_widget
    from bauh.view.qt.view_model import PackageView
    from bauh.view.qt.window.constants import ACTION_INSTALL, BT_MATUGEN, DISPLAY_NAME
    from bauh.view.qt.window.manage_window import ManageWindow
    from bauh.view.util.translation import I18n


def new_config() -> dict:
    return {'ui': {'table': {'max_displayed': 50}, 'theme': 'light'},
            'download': {'icons': True},
            'memory_cache': {'data_expiration': 60},
            'disk': {'store_history': False},
            'suggestions': {'enabled': False},
            'system': {'notifications': False}}


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestManageWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # necesario para instanciar componentes Qt
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.i18n = MagicMock(spec=I18n)
        self.i18n.get.side_effect = lambda key, default=None: default if default is not None else key
        self.i18n.__getitem__.side_effect = lambda key: key

        self.config = new_config()
        self.context = MagicMock(spec=ApplicationContext)
        self.context.internet_checker = MagicMock()
        self.logger = logging.getLogger('test')

        self.window = ManageWindow(i18n=self.i18n,
                                   icon_cache=MagicMock(spec=MemoryCache),
                                   manager=MagicMock(spec=SoftwareManager),
                                   config=self.config,
                                   context=self.context,
                                   http_client=MagicMock(spec=HttpClient),
                                   logger=self.logger,
                                   icon=QIcon())

    def tearDown(self):
        self.window.deleteLater()

    def _new_package_view(self, name: str, categories) -> PackageView:
        model = MagicMock(spec=SoftwarePackage)
        model.name = name
        model.categories = categories
        model.installed = True
        model.update = False
        model.status = PackageStatus.READY
        model.is_application.return_value = True
        model.is_update_ignored.return_value = True
        model.is_trustable.return_value = True
        model.get_type.return_value = 'arch'
        return PackageView(model=model, i18n=self.i18n)

    def test_instantiation_with_mixins(self):
        self.assertEqual(50, self.window.display_limit)
        self.assertTrue(hasattr(self.window, '_handle_updates_filter'))  # de WindowFiltersMixin
        self.assertTrue(hasattr(self.window, 'begin_uninstall'))  # de WindowActionsMixin
        self.assertTrue(hasattr(self.window, '_change_status'))  # de WindowUIMixin

    def test_window_title_is_the_fork_display_name(self):
        self.assertEqual(DISPLAY_NAME, self.window.windowTitle())

    def test_add_category_is_not_name_mangled(self):
        # el metodo vive en el mixin: con doble guion bajo el name-mangling lo hacia inalcanzable
        self.assertTrue(hasattr(self.window, '_add_category'))
        self.assertFalse(hasattr(self.window, '_ManageWindow__add_category'))

    def test_finish_ignore_updates_registers_new_categories(self):
        self.window._update_categories({'games'})
        self.assertEqual(2, self.window.combo_categories.count())

        pkgv = self._new_package_view('some-package', ['Utility'])
        res = {'success': True, 'pkg': pkgv, 'action': 'ignore_updates'}

        with patch('bauh.view.qt.dialog.show_message') as show_message:
            self.window.finish_ignore_updates(res)

        show_message.assert_called_once()

        categories = {self.window.combo_categories.itemData(idx)
                      for idx in range(1, self.window.combo_categories.count())}
        self.assertIn('utility', categories)
        self.assertIn('games', categories)

    def test_matugen_button_is_registered_in_the_components_manager(self):
        self.assertIn(BT_MATUGEN, self.window.comp_manager.components)

    def test_matugen_button_has_no_hardcoded_emoji(self):
        self.assertNotIn('🎨', self.window.bt_matugen.text())
        self.assertNotIn('🎨', self.window.bt_matugen.toolTip())

    def test_handle_matugen_toggle_persists_the_theme(self):
        self.window.thread_save_theme = MagicMock()

        with patch('bauh.view.qt.window.manage_window.set_theme') as set_theme:
            self.window._handle_matugen_toggle()

        set_theme.assert_called_once()
        self.assertEqual(self.config, set_theme.call_args.kwargs['app_config'])
        self.assertEqual('matugen', self.config['ui']['theme'])
        self.assertEqual('matugen', self.window.thread_save_theme.theme_key)
        self.window.thread_save_theme.start.assert_called_once()

    def test_close_event_is_ignored_when_the_user_denies_the_confirmation(self):
        self.window.current_action_id = ACTION_INSTALL
        event = QCloseEvent()
        event.accept()

        with patch('bauh.view.qt.window.manage_window.ConfirmationDialog') as dialog_cls:
            dialog_cls.return_value.ask.return_value = False
            self.window.closeEvent(event)

        self.assertFalse(event.isAccepted())

    def test_close_event_is_accepted_when_the_user_confirms(self):
        self.window.current_action_id = ACTION_INSTALL
        event = QCloseEvent()

        with patch('bauh.view.qt.window.manage_window.ConfirmationDialog') as dialog_cls:
            dialog_cls.return_value.ask.return_value = True
            self.window.closeEvent(event)

        self.assertTrue(event.isAccepted())

    def test_close_event_does_not_ask_when_there_is_no_transaction(self):
        self.window.current_action_id = None
        event = QCloseEvent()

        with patch('bauh.view.qt.window.manage_window.ConfirmationDialog') as dialog_cls:
            self.window.closeEvent(event)

        dialog_cls.assert_not_called()
        self.assertTrue(event.isAccepted())


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestSpacerComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_new_spacer_is_expanding_and_styleable(self):
        spacer = new_spacer()
        self.assertEqual('true', spacer.property('spacer'))
        self.assertEqual(QSizePolicy.Expanding, spacer.sizePolicy().horizontalPolicy())
        self.assertEqual(QSizePolicy.Expanding, spacer.sizePolicy().verticalPolicy())

    def test_new_spacer_applies_the_minimum_width(self):
        spacer = new_spacer(min_width=30)
        self.assertEqual(30, spacer.minimumWidth())

    def test_to_widget_renders_a_spacer_component(self):
        widget = to_widget(SpacerComponent(), i18n=MagicMock())
        self.assertEqual('true', widget.property('spacer'))


if __name__ == '__main__':
    unittest.main()
