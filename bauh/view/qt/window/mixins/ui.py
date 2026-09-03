from typing import List
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QWidget, QCheckBox, QHeaderView, QApplication, QMenu
from bauh.api.abstract.view import MessageType
from bauh.context import set_theme
from bauh.view.qt.window.constants import CHECK_DETAILS, BT_CUSTOM_ACTIONS, GROUP_LOWER_BTS
from bauh.stylesheet import read_all_themes_metadata, ThemeMetadata
from bauh.view.core.config import CoreConfigManager
from bauh.view.qt import dialog
from bauh.view.qt.about import AboutDialog
from bauh.view.qt.components import to_widget, QCustomMenuAction
from bauh.view.qt.dialog import ConfirmationDialog
from bauh.view.qt.qt_utils import get_current_screen_geometry
from bauh.view.qt.settings import SettingsWindow
from bauh.api.abstract.model import CustomSoftwareAction

class WindowUIMixin:
    """Presentacion y dialogos secundarios de la ventana principal.

    Contrato con la clase anfitriona (ManageWindow), que debe definir:
      - atributos de estado: 'i18n', 'config', 'context', 'manager', 'custom_actions', 'dialog_about',
        'settings_window', 'progress_controll_enabled', '_maximized', 'pkgs'
      - widgets: 'icon_status', 'label_status', 'label_substatus', 'toolbar_substatus', 'toolbar_filters',
        'toolbar_status', 'table_apps', 'table_container', 'textarea_details', 'check_details', 'progress_bar'
      - colaboradores: 'comp_manager' (QtComponentsManager), 'thread_animate_progress', 'thread_save_theme'
      - senales: 'signal_user_res'
      - metodos: 'begin_execute_custom_action'
    """

    def _update_process_progress(self, val: int):
        if self.progress_controll_enabled:
            self.thread_animate_progress.set_progress(val)

    def _change_status(self, status: str=None):
        if status:
            self.icon_status.setVisible(True)
            self.label_status.setText(status + '...')
            self.label_status.setCursor(QCursor(Qt.WaitCursor))
        else:
            self.icon_status.setVisible(False)
            self.label_status.setText('')
            self.label_status.unsetCursor()

    def _set_table_enabled(self, enabled: bool):
        self.table_apps.setEnabled(enabled)
        if enabled:
            self.table_container.unsetCursor()
        else:
            self.table_container.setCursor(QCursor(Qt.WaitCursor))

    def _ask_confirmation(self, msg: dict):
        self.thread_animate_progress.pause()
        extra_widgets = [to_widget(comp=c, i18n=self.i18n) for c in msg['components']] if msg.get('components') else None
        diag = ConfirmationDialog(title=msg['title'], body=msg['body'], i18n=self.i18n, widgets=extra_widgets, confirmation_label=msg['confirmation_label'], deny_label=msg['deny_label'], deny_button=msg['deny_button'], window_cancel=msg['window_cancel'], confirmation_button=msg.get('confirmation_button', True), min_width=msg.get('min_width'), min_height=msg.get('min_height'), max_width=msg.get('max_width'))
        diag.ask()
        res = diag.confirmed
        self.thread_animate_progress.animate()
        self.signal_user_res.emit(res)

    def _show_message(self, msg: dict):
        self.thread_animate_progress.pause()
        dialog.show_message(title=msg['title'], body=msg['body'], type_=msg['type'])
        self.thread_animate_progress.animate()

    def _show_warnings(self, warnings: List[str]):
        if warnings:
            dialog.show_message(title=self.i18n['warning'].capitalize(), body='<p>{}</p>'.format('<br/><br/>'.join(warnings)), type_=MessageType.WARNING)

    def _show_about(self):
        if self.dialog_about is None:
            self.dialog_about = AboutDialog(self.config)
        self.dialog_about.show()

    def _handle_console(self, checked: bool):
        if checked:
            self.textarea_details.show()
        else:
            self.textarea_details.hide()

    def _handle_console_option(self, enable: bool):
        if enable:
            self.textarea_details.clear()
        self.comp_manager.set_component_visible(CHECK_DETAILS, enable)
        self.check_details.setChecked(False)
        self.textarea_details.hide()

    def _change_label_status(self, status: str):
        self.label_status.setText(status)

    def _change_label_substatus(self, substatus: str):
        self.label_substatus.setText('<p>{}</p>'.format(substatus))
        if not substatus:
            self.toolbar_substatus.hide()
        elif not self.toolbar_substatus.isVisible() and self.progress_bar.isVisible():
            self.toolbar_substatus.show()

    def _reorganize(self):
        if not self._maximized:
            self.table_apps.change_headers_policy(QHeaderView.Stretch)
            self.table_apps.change_headers_policy()
            self._resize(accept_lower_width=len(self.pkgs) > 0)

    def _change_checkbox(self, checkbox: QCheckBox, checked: bool, attr: str=None, trigger: bool=True):
        if not trigger:
            checkbox.blockSignals(True)
        checkbox.setChecked(checked)
        if not trigger:
            setattr(self, attr, checked)
            checkbox.blockSignals(False)

    def _resize(self, accept_lower_width: bool=True):
        table_width = self.table_apps.get_width()
        toolbar_width = self.toolbar_filters.sizeHint().width()
        topbar_width = self.toolbar_status.sizeHint().width()
        new_width = max(table_width, toolbar_width, topbar_width)
        new_width *= 1.05  # this extra size is not because of the toolbar button, but the table upgrade buttons
        new_width = int(new_width)
        if new_width >= self.maximumWidth():
            new_width = self.maximumWidth()
        if self.pkgs and accept_lower_width or new_width > self.width():
            self.resize(new_width, self.height())
            self.setMinimumWidth(new_width)

    def set_progress_controll(self, enabled: bool):
        self.progress_controll_enabled = enabled

    def _show_console_errors(self):
        if self.textarea_details.toPlainText():
            self.check_details.setChecked(True)
        else:
            self._handle_console_option(False)
            self.comp_manager.set_component_visible(CHECK_DETAILS, False)

    def _set_lower_buttons_visible(self, visible: bool):
        self.comp_manager.set_group_visible(GROUP_LOWER_BTS, visible)
        if visible:
            self.comp_manager.set_component_visible(BT_CUSTOM_ACTIONS, bool(self.custom_actions))

    def _update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def show_settings(self):
        if self.settings_window:
            self.settings_window.handle_display()
        else:
            self.settings_window = SettingsWindow(manager=self.manager, i18n=self.i18n, window=self)
            screen_width = get_current_screen_geometry(self).width()
            self.settings_window.setMinimumWidth(int(screen_width / 4))
            self.settings_window.resize(self.size())
            self.settings_window.adjustSize()
            self.settings_window.show()

    def _map_custom_action(self, action: CustomSoftwareAction, parent: QWidget) -> QCustomMenuAction:
        if action.icon_path:
            try:
                if action.icon_path.startswith('/'):
                    icon = QIcon(action.icon_path)
                else:
                    icon = QIcon.fromTheme(action.icon_path)
            except Exception:
                icon = None
        else:
            icon = None
        tip = self.i18n[action.i18n_description_key] if action.i18n_description_key else None
        return QCustomMenuAction(parent=parent, label=self.i18n[action.i18n_label_key], action=lambda: self.begin_execute_custom_action(None, action), tooltip=tip, icon=icon)

    def show_custom_actions(self):
        if self.custom_actions:
            menu_row = QMenu()
            menu_row.setCursor(QCursor(Qt.PointingHandCursor))
            actions = [self._map_custom_action(a, menu_row) for a in self.custom_actions]
            menu_row.addActions(actions)
            menu_row.adjustSize()
            menu_row.popup(QCursor.pos())
            menu_row.exec_()

    def _map_theme_action(self, theme: ThemeMetadata, menu: QMenu) -> QCustomMenuAction:

        def _change_theme():
            # el config en memoria debe reflejar el tema elegido: si no, el watcher de gtk.css
            # vuelve a aplicar el tema anterior y se pierden los overrides de 'custom_theme'
            self.config['ui']['theme'] = theme.key
            set_theme(theme_key=theme.key, app=QApplication.instance(), logger=self.context.logger,
                      app_config=self.config)
            self.thread_save_theme.theme_key = theme.key
            self.thread_save_theme.start()
        return QCustomMenuAction(label=theme.get_i18n_name(self.i18n), action=_change_theme, parent=menu, tooltip=theme.get_i18n_description(self.i18n))

    def show_themes(self):
        menu_row = QMenu()
        menu_row.setCursor(QCursor(Qt.PointingHandCursor))
        menu_row.addActions(self._map_theme_actions(menu_row))
        menu_row.adjustSize()
        menu_row.popup(QCursor.pos())
        menu_row.exec_()

    def _map_theme_actions(self, menu: QMenu) -> List[QCustomMenuAction]:
        core_config = CoreConfigManager().get_config()
        current_theme_key, current_action = (core_config['ui']['theme'], None)
        actions = []
        for t in read_all_themes_metadata():
            if not t.abstract:
                action = self._map_theme_action(t, menu)
                if current_action is None and current_theme_key is not None and (current_theme_key == t.key):
                    action.button.setProperty('current', 'true')
                    current_action = action
                else:
                    actions.append(action)
        if not current_action:
            invalid_action = QCustomMenuAction(label=self.i18n['manage_window.bt_themes.option.invalid'], parent=menu)
            invalid_action.button.setProperty('current', 'true')
            current_action = invalid_action
        actions.sort(key=lambda a: a.get_label())
        actions.insert(0, current_action)
        return actions