# Las anotaciones se evalúan de forma perezosa: la clase de test se salta cuando no
# hay PyQt5, pero su CUERPO sí se ejecuta al importar el módulo, y sin este import
# una anotación como «-> PackageView» rompería la recolección con NameError.
from __future__ import annotations

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
    from bauh.api.abstract.view import MessageType, SpacerComponent
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

    def _toggle_matugen(self, colors=None):
        """Pulsa el interruptor Matugen sin tocar el tema real ni abrir diálogos."""
        found = {'accent_color': '#BEC4EE'} if colors is None else colors

        with patch('bauh.view.qt.window.manage_window.set_theme') as set_theme, \
                patch('bauh.view.qt.window.manage_window.parse_gtk_matugen_colors', return_value=found), \
                patch('bauh.view.qt.dialog.show_message') as show_message:
            self.window._handle_matugen_toggle()

        return set_theme, show_message

    def test_handle_matugen_toggle_persists_the_theme(self):
        self.window.thread_save_theme = MagicMock()

        set_theme, show_message = self._toggle_matugen()

        set_theme.assert_called_once()
        self.assertEqual(self.config, set_theme.call_args.kwargs['app_config'])
        self.assertEqual('matugen', self.config['ui']['theme'])
        self.assertEqual('matugen', self.window.thread_save_theme.theme_key)
        self.window.thread_save_theme.start.assert_called_once()
        show_message.assert_not_called()

    def test_matugen_button_is_a_toggle_that_restores_the_previous_theme(self):
        self.window.thread_save_theme = MagicMock()
        self.assertTrue(self.window.bt_matugen.isCheckable())
        self.assertFalse(self.window.bt_matugen.isChecked())  # el tema de partida es 'light'

        self._toggle_matugen()
        self.assertEqual('matugen', self.config['ui']['theme'])
        self.assertTrue(self.window.bt_matugen.isChecked())

        set_theme, _ = self._toggle_matugen()
        self.assertEqual('light', set_theme.call_args.kwargs['theme_key'])
        self.assertEqual('light', self.config['ui']['theme'])
        self.assertFalse(self.window.bt_matugen.isChecked())

    def test_turning_matugen_off_without_a_previous_theme_goes_back_to_aurora(self):
        self.window.thread_save_theme = MagicMock()
        self.config['ui']['theme'] = 'matugen'
        self.window._sync_matugen_button()
        self.assertTrue(self.window.bt_matugen.isChecked())

        set_theme, _ = self._toggle_matugen()

        self.assertEqual('aurora', set_theme.call_args.kwargs['theme_key'])
        self.assertFalse(self.window.bt_matugen.isChecked())

    def test_matugen_without_colors_explains_why_it_looks_like_aurora(self):
        self.window.thread_save_theme = MagicMock()

        _, show_message = self._toggle_matugen(colors={})

        show_message.assert_called_once()
        self.assertEqual('manage_window.matugen.no_colors.body', show_message.call_args.kwargs['body'])
        self.assertEqual(MessageType.INFO, show_message.call_args.kwargs['type_'])

    def test_a_failing_theme_leaves_the_toggle_as_it_was(self):
        self.window.thread_save_theme = MagicMock()

        with patch('bauh.view.qt.window.manage_window.set_theme', side_effect=RuntimeError('boom')), \
                patch('bauh.view.qt.dialog.show_message') as show_message:
            self.window._handle_matugen_toggle()

        self.assertEqual('light', self.config['ui']['theme'])
        self.assertFalse(self.window.bt_matugen.isChecked())
        self.window.thread_save_theme.start.assert_not_called()
        show_message.assert_not_called()

    def test_the_themes_menu_offers_to_connect_matugen_only_when_it_is_installed(self):
        with patch('bauh.view.qt.window.mixins.ui.matugen.is_installed', return_value=False):
            self.assertIsNone(self.window._map_matugen_action(None))

        with patch('bauh.view.qt.window.mixins.ui.matugen.is_installed', return_value=True), \
                patch('bauh.view.qt.window.mixins.ui.matugen.is_registered', return_value=False):
            action = self.window._map_matugen_action(None)
        self.assertEqual('manage_window.bt_themes.matugen.connect', action.button.text())
        self.assertTrue(action.button.isEnabled())

        with patch('bauh.view.qt.window.mixins.ui.matugen.is_installed', return_value=True), \
                patch('bauh.view.qt.window.mixins.ui.matugen.is_registered', return_value=True):
            action = self.window._map_matugen_action(None)
        self.assertEqual('manage_window.bt_themes.matugen.connected', action.button.text())
        self.assertFalse(action.button.isEnabled())

    def test_the_filters_have_no_dashes(self):
        self.assertEqual('manage_window.filter.any_type', self.window.combo_filter_type.itemText(0))
        self.assertEqual('manage_window.filter.any_category', self.window.combo_categories.itemText(0))

    def test_empty_table_message_depends_on_how_the_list_was_reached(self):
        self.assertEqual('manage_window.table.empty.filters', self.window._empty_table_message())

        self.window.filter_updates = True
        self.assertEqual('manage_window.table.empty.updates', self.window._empty_table_message())

        self.i18n.__getitem__.side_effect = lambda key: key + ' {}'
        self.window.search_performed = True
        self.window.searched_term = 'firefox'
        self.assertEqual('manage_window.table.empty.search firefox', self.window._empty_table_message())

    def test_there_is_no_suggestions_button(self):
        from bauh.view.qt.components import IconButton
        from bauh.view.qt.window import constants

        names = {b.objectName() for b in self.window.findChildren(IconButton)}
        self.assertNotIn('suggestions', names)
        self.assertFalse(hasattr(constants, 'BT_SUGGESTIONS'))
        self.assertFalse(hasattr(self.window, 'begin_load_suggestions'))

    def test_there_is_a_single_search_box(self):
        self.assertFalse(hasattr(self.window, 'input_name'))
        from bauh.view.qt.window import constants
        self.assertFalse(hasattr(constants, 'INP_NAME'))

    def test_typing_schedules_a_filter_of_what_is_shown(self):
        self.window.search_bar.inp_search.textEdited.emit('  fire ')

        self.assertEqual('fire', self.window._name_filter)
        self.assertTrue(self.window._timer_name_filter.isActive())
        self.assertEqual('fire', self.window._gen_filters().name)
        self.window._timer_name_filter.stop()

    def test_pressing_enter_searches_and_drops_the_pending_filter(self):
        self.window.search_bar.inp_search.textEdited.emit('fire')
        self.window.thread_search = MagicMock()
        self.window.search_bar.set_text('firefox')

        # _begin_action arranca el hilo real de la animación de progreso: si sigue vivo cuando
        # la ventana se destruye, Qt aborta el proceso entero en la prueba siguiente
        with patch.object(self.window, '_begin_action'):
            self.window.search()

        self.assertFalse(self.window._timer_name_filter.isActive())
        self.assertEqual('', self.window._name_filter)
        self.assertEqual('firefox', self.window.thread_search.word)
        self.window.thread_search.start.assert_called_once()

    def test_the_live_filter_runs_the_filter_thread_without_hiding_the_search_box(self):
        self.window.pkgs_available = [self._new_package_view('firefox', [])]
        self.window.thread_apply_filters = MagicMock()
        self.window.thread_apply_filters.isRunning.return_value = False
        self.window._name_filter = 'fire'

        with patch.object(self.window, '_begin_action') as begin_action:
            self.window._apply_live_name_filter()

        begin_action.assert_not_called()  # _begin_action oculta el buscador
        self.window.thread_apply_filters.start.assert_called_once()
        self.assertEqual('fire', self.window.thread_apply_filters.filters.name)

    def test_the_live_filter_waits_for_a_running_action(self):
        self.window.pkgs_available = [self._new_package_view('firefox', [])]
        self.window.thread_apply_filters = MagicMock()
        self.window.current_action_id = 1

        self.window._apply_live_name_filter()

        self.window.thread_apply_filters.start.assert_not_called()
        self.assertTrue(self.window._timer_name_filter.isActive())
        self.window._timer_name_filter.stop()

    def test_the_live_filter_does_nothing_without_packages(self):
        self.window.pkgs_available = []
        self.window.thread_apply_filters = MagicMock()

        self.window._apply_live_name_filter()

        self.window.thread_apply_filters.start.assert_not_called()

    def _row_package(self, has_info=True, has_screenshots=True):
        pkgv = self._new_package_view('firefox', [])
        pkgv.model.gem_name = 'arch'
        pkgv.model.has_info.return_value = has_info
        pkgv.model.has_screenshots.return_value = has_screenshots
        pkgv.model.get_type_icon_path.return_value = ''
        pkgv.model.get_default_icon_path.return_value = ''
        pkgv.model.icon_url = None
        pkgv.model.version = '1.0'
        pkgv.model.description = 'browser'
        pkgv.model.get_display_name.return_value = 'firefox'
        pkgv.model.get_name_tooltip.return_value = 'firefox'
        pkgv.model.get_publisher.return_value = 'extra'
        pkgv.model.supports_disk_cache.return_value = False
        pkgv.model.get_custom_actions.return_value = []
        return pkgv

    def test_the_type_is_a_badge_on_the_icon_not_a_column(self):
        from bauh.view.qt.apps_table import PackagesTable
        table = self.window.table_apps
        pkgv = self._row_package()

        table.update_packages([pkgv], update_check_enabled=False)

        self.assertEqual(PackagesTable.COL_NUMBER, 8)
        self.assertEqual(7, table.columnCount())  # sin la columna de actualizar
        icon = table._icon_label(0)
        self.assertEqual('app_icon', icon.objectName())
        self.assertIn('type', icon.toolTip())

    def test_the_badge_is_only_drawn_over_a_real_icon(self):
        from PyQt5.QtGui import QColor, QIcon, QPixmap
        table = self.window.table_apps
        red, blue = QPixmap(28, 28), QPixmap(14, 14)
        red.fill(QColor('#FF0000'))
        blue.fill(QColor('#0000FF'))

        plain = table._icon_pixmap(QIcon(red), None).toImage()
        badged = table._icon_pixmap(QIcon(red), blue).toImage()

        self.assertEqual('#ff0000', plain.pixelColor(27, 27).name())
        self.assertEqual('#0000ff', badged.pixelColor(27, 27).name())
        self.assertEqual('#ff0000', badged.pixelColor(2, 2).name())

    def test_the_info_button_opens_the_screenshots_when_there_is_no_info(self):
        table = self.window.table_apps
        table.update_packages([self._row_package(has_info=False, has_screenshots=True)], update_check_enabled=False)
        from bauh.view.qt.components import IconButton
        actions = table.cellWidget(0, 6)
        bt_info = [b for b in actions.findChildren(IconButton) if b.objectName() == 'app_info'][0]

        self.assertTrue(bt_info.isEnabled())
        self.assertFalse([b for b in actions.findChildren(IconButton) if b.objectName() == 'app_screenshots'])

        with patch.object(self.window, 'begin_show_screenshots') as screenshots, \
                patch.object(self.window, 'begin_show_info') as info:
            bt_info.click()

        screenshots.assert_called_once()
        info.assert_not_called()

    def test_the_info_dialog_can_open_the_screenshots(self):
        pkgv = self._row_package()
        created = []

        class FakeInfoDialog:
            def __init__(self, **kwargs):
                created.append(kwargs)
                self.screenshots_requested = True

            def exec_(self):
                pass

        with patch('bauh.view.qt.window.mixins.actions.InfoDialog', FakeInfoDialog), \
                patch.object(self.window, 'begin_show_screenshots') as screenshots:
            self.window._finish_show_info({'__app__': pkgv, 'version': '1.0'})

        self.assertTrue(created[0]['show_screenshots'])
        screenshots.assert_called_once_with(pkgv)

    def test_the_empty_table_shows_its_message_only_without_rows(self):
        table = self.window.table_apps
        table.empty_message = 'Todo está al día'

        table.update_packages([])
        self.assertTrue(table.label_empty.isVisibleTo(table))
        self.assertEqual('Todo está al día', table.label_empty.text())

        table.show_empty_message(None)
        self.assertFalse(table.label_empty.isVisibleTo(table))

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
