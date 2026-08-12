import logging
import operator
import os.path
import shutil
import time
from pathlib import Path
from typing import List, Type, Set, Tuple, Optional, Dict, Any
from PyQt5.QtCore import QEvent, Qt, pyqtSignal, QRect
from PyQt5.QtGui import QIcon, QWindowStateChangeEvent, QCursor, QCloseEvent, QShowEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QHeaderView, QToolBar, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QComboBox, QApplication, QListView, QSizePolicy, QMenu, QHBoxLayout, QFrame
from bauh.api import user
from bauh.api.abstract.cache import MemoryCache
from bauh.api.abstract.context import ApplicationContext
from bauh.api.abstract.controller import SoftwareManager, SoftwareAction
from bauh.api.abstract.model import SoftwarePackage
from bauh.api.abstract.view import MessageType
from bauh.api.http import HttpClient
from bauh.api.paths import LOGS_DIR
from bauh.commons.html import bold
from bauh.context import set_theme
from bauh.view.qt.window.constants import *
from bauh.stylesheet import read_all_themes_metadata, ThemeMetadata
from bauh.view.core.config import CoreConfigManager
from bauh.view.core.tray_client import notify_tray
from bauh.view.qt import dialog, commons, qt_utils
from bauh.view.qt.about import AboutDialog
from bauh.view.qt.apps_table import PackagesTable, UpgradeToggleButton
from bauh.view.qt.commons import sum_updates_displayed, PackageFilters
from bauh.view.qt.components import new_spacer, IconButton, QtComponentsManager, to_widget, QSearchBar, QCustomMenuAction, QCustomToolbar
from bauh.view.qt.dialog import ConfirmationDialog
from bauh.view.qt.history import HistoryDialog
from bauh.view.qt.info import InfoDialog
from bauh.view.qt.qt_utils import get_current_screen_geometry
from bauh.view.qt.root import RootDialog
from bauh.view.qt.screenshots import ScreenshotsDialog
from bauh.view.qt.settings import SettingsWindow
from bauh.view.qt.thread import UpgradeSelected, RefreshApps, UninstallPackage, DowngradePackage, ShowPackageInfo, ShowPackageHistory, SearchPackages, InstallPackage, AnimateProgress, NotifyPackagesReady, FindSuggestions, ListWarnings, AsyncAction, LaunchPackage, ApplyFilters, CustomSoftwareAction, ShowScreenshots, CustomAction, NotifyInstalledLoaded, IgnorePackageUpdates, SaveTheme, StartAsyncAction
from bauh.view.qt.view_index import add_to_index, new_package_index
from bauh.view.qt.view_model import PackageView, PackageViewStatus
from bauh.view.util import util, resource
from bauh.view.util.translation import I18n

class WindowActionsMixin:

    def _bind_async_action(self, action: AsyncAction, finished_call, only_finished: bool=False) -> AsyncAction:
        action.signal_finished.connect(finished_call)
        if not only_finished:
            action.signal_confirmation.connect(self._ask_confirmation)
            action.signal_output.connect(self._update_action_output)
            action.signal_message.connect(self._show_message)
            action.signal_status.connect(self._change_label_status)
            action.signal_substatus.connect(self._change_label_substatus)
            action.signal_progress.connect(self._update_process_progress)
            action.signal_progress_control.connect(self.set_progress_controll)
            action.signal_root_password.connect(self._pause_and_ask_root_password)
            self.signal_user_res.connect(action.confirm)
            self.signal_root_password.connect(action.set_root_password)
        return action

    def _pause_and_ask_root_password(self):
        self.thread_animate_progress.pause()
        valid, password = RootDialog.ask_password(self.context, i18n=self.i18n, comp_manager=self.comp_manager, parent=self)
        self.thread_animate_progress.animate()
        self.signal_root_password.emit(valid, password)

    def begin_refresh_packages(self, pkg_types: Optional[Set[Type[SoftwarePackage]]]=None):
        self.table_apps.stop_file_downloader()
        self.search_bar.clear()
        self._begin_action(self.i18n['manage_window.status.refreshing'])
        self.comp_manager.set_components_visible(False)
        self._handle_console_option(False)
        self.suggestions_requested = False
        self.search_performed = False
        self.thread_refresh.pkg_types = pkg_types
        self.thread_refresh.start()

    def _finish_refresh_packages(self, res: dict, as_installed: bool=True):
        self._finish_action()
        self._set_lower_buttons_visible(True)
        self.comp_manager.set_component_visible(SEARCH_BAR, True)
        if self.search_performed or self.suggestions_requested:
            self.comp_manager.set_group_visible(GROUP_VIEW_SEARCH, True)
        else:
            self.comp_manager.set_group_visible(GROUP_VIEW_INSTALLED, True)
        if self.update_pkgs(res['installed'], as_installed=as_installed, types=res['types']):
            self._hide_filters_no_packages()
            self._update_bts_installed_and_suggestions()
            self._reorganize()
        if self.first_refresh:
            self.first_refresh = False
            qt_utils.centralize(self)
        self.load_suggestions = False
        self.types_changed = False

    def load_without_packages(self):
        self.load_suggestions = False
        self._handle_console_option(False)
        self._finish_refresh_packages({'installed': None, 'types': None}, as_installed=False)

    def begin_load_suggestions(self, filter_installed: bool):
        self.table_apps.stop_file_downloader()
        self.search_bar.clear()
        self._begin_action(self.i18n['manage_window.status.suggestions'])
        self._handle_console_option(False)
        self.comp_manager.set_components_visible(False)
        self.suggestions_requested = True
        self.thread_suggestions.filter_installed = filter_installed
        self.thread_suggestions.start()

    def _finish_load_suggestions(self, res: dict):
        self._finish_search(res)

    def begin_uninstall(self, pkg: PackageView):
        pwd, proceed = self._ask_root_password(SoftwareAction.UNINSTALL, pkg)
        if not proceed:
            return
        self._begin_action(action_label='{} {}'.format(self.i18n['manage_window.status.uninstalling'], pkg.model.name), action_id=ACTION_UNINSTALL)
        self.comp_manager.set_groups_visible(False, GROUP_UPPER_BAR, GROUP_LOWER_BTS)
        self._handle_console_option(True)
        self.thread_uninstall.pkg = pkg
        self.thread_uninstall.root_pwd = pwd
        self.thread_uninstall.start()

    def _finish_uninstall(self, res: dict):
        self._finish_action(action_id=ACTION_UNINSTALL)
        self._write_operation_logs('uninstall', res['pkg'])
        if res['success']:
            src_pkg = res['pkg']
            if self._can_notify_user():
                util.notify_user('{} ({}) {}'.format(src_pkg.model.name, src_pkg.model.get_type(), self.i18n['uninstalled']))
            if res['removed']:
                screen_width = get_current_screen_geometry(self).width()
                for list_idx, pkg_list in enumerate((self.pkgs_available, self.pkgs, self.pkgs_installed)):
                    if pkg_list:
                        removed_idxs = []
                        for pkgv_idx, pkgv in enumerate(pkg_list):
                            if len(removed_idxs) == len(res['removed']):
                                break
                            for model in res['removed']:
                                if pkgv.model == model:
                                    if list_idx == 0:
                                        pkgv.update_model(model)
                                    if not self.search_performed or list_idx == 2:
                                        removed_idxs.append(pkgv_idx)
                                    if self.search_performed and list_idx == 1:
                                        self.table_apps.update_package(pkgv, screen_width=screen_width, change_update_col=True)
                                    break
                        if removed_idxs:
                            removed_idxs.sort()
                            for decrement, pkg_idx in enumerate(removed_idxs):
                                del pkg_list[pkg_idx - decrement]
                            if list_idx == 1:
                                for decrement, idx in enumerate(removed_idxs):
                                    self.table_apps.removeRow(idx - decrement)
                                self._update_table_indexes()
                        self.update_bt_upgrade()
            self.update_custom_actions()
            self._show_console_checkbox_if_output()
            self._update_installed_filter()
            self._update_index()
            self.begin_apply_filters()
            self.table_apps.change_headers_policy(policy=QHeaderView.Stretch, maximized=self._maximized)
            self.table_apps.change_headers_policy(policy=QHeaderView.ResizeToContents, maximized=self._maximized)
            self._resize(accept_lower_width=True)
            notify_tray()
        else:
            self._show_console_errors()
            if self._can_notify_user():
                util.notify_user('{}: {}'.format(res['pkg'].model.name, self.i18n['notification.uninstall.failed']))

    def begin_launch_package(self, pkg: PackageView):
        self._begin_action(action_label=self.i18n['manage_window.status.running_app'].format(pkg.model.name), action_id=ACTION_LAUNCH)
        self.comp_manager.disable_visible()
        self.thread_launch.pkg = pkg
        self.thread_launch.start()

    def _finish_launch_package(self, success: bool):
        self._finish_action(action_id=ACTION_LAUNCH)

    def upgrade_selected(self):
        body = QWidget()
        body.setLayout(QHBoxLayout())
        body.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        body.layout().addWidget(QLabel(self.i18n['manage_window.upgrade_all.popup.body']))
        body.layout().addWidget(UpgradeToggleButton(pkg=None, root=self, i18n=self.i18n, clickable=False))
        if ConfirmationDialog(title=self.i18n['manage_window.upgrade_all.popup.title'], i18n=self.i18n, body=None, widgets=[body]).ask():
            self._begin_action(action_label=self.i18n['manage_window.status.upgrading'], action_id=ACTION_UPGRADE)
            self.comp_manager.set_components_visible(False)
            self._handle_console_option(True)
            self.thread_update.pkgs = self.pkgs
            self.thread_update.start()

    def _finish_upgrade_selected(self, res: dict):
        self._finish_action()
        if res.get('id'):
            self._write_operation_logs('upgrade', custom_log_file=f"{UpgradeSelected.UPGRADE_LOGS_DIR}/{res['id']}.log")
            sum_log_file = UpgradeSelected.SUMMARY_FILE.format(res['id'])
            summ_msg = '* ' + self.i18n['console.upgrade_summary'].format(path=f'"{sum_log_file}"')
            self.textarea_details.appendPlainText(summ_msg)
        if res['success']:
            self.comp_manager.remove_saved_state(ACTION_UPGRADE)
            self.begin_refresh_packages(pkg_types=res['types'])
            self._show_console_checkbox_if_output()
            if self._can_notify_user():
                util.notify_user('{} {}'.format(res['updated'], self.i18n['notification.update_selected.success']))
            notify_tray()
        else:
            self.comp_manager.restore_state(ACTION_UPGRADE)
            self._show_console_errors()
            if self._can_notify_user():
                util.notify_user(self.i18n['notification.update_selected.failed'])
        self.update_custom_actions()

    def _update_action_output(self, output: str):
        self.textarea_details.appendPlainText(output)

    def _begin_action(self, action_label: str, action_id: int=None):
        self.thread_animate_progress.stop = False
        self.thread_animate_progress.start()
        self.progress_bar.setVisible(True)
        if action_id is not None:
            self.comp_manager.save_states(action_id, only_visible=True)
        self._set_table_enabled(False)
        self.comp_manager.set_component_visible(SEARCH_BAR, False)
        self._change_status(action_label)

    def _finish_action(self, action_id: int=None):
        self.thread_animate_progress.stop = True
        self.thread_animate_progress.wait(msecs=1000)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        if action_id is not None:
            self.comp_manager.restore_state(action_id)
        self.comp_manager.set_component_visible(SEARCH_BAR, True)
        self._change_status()
        self._change_label_substatus('')
        self._set_table_enabled(True)
        self.progress_controll_enabled = True

    def begin_downgrade(self, pkg: PackageView):
        pwd, proceed = self._ask_root_password(SoftwareAction.DOWNGRADE, pkg)
        if not proceed:
            return
        self.table_apps.stop_file_downloader()
        label = f"{self.i18n['manage_window.status.downgrading']} {pkg.model.name}"
        self._begin_action(action_label=label, action_id=ACTION_DOWNGRADE)
        self.comp_manager.set_components_visible(False)
        self._handle_console_option(True)
        self.thread_downgrade.pkg = pkg
        self.thread_downgrade.root_pwd = pwd
        self.thread_downgrade.start()

    def _finish_downgrade(self, res: dict):
        self._finish_action()
        self._write_operation_logs('downgrade', res['app'])
        if res['success']:
            self.comp_manager.remove_saved_state(ACTION_DOWNGRADE)
            if self._can_notify_user():
                util.notify_user('{} {}'.format(res['app'], self.i18n['downgraded']))
            self.begin_refresh_packages(pkg_types={res['app'].model.__class__} if len(self.pkgs) > 1 else None)
            self._show_console_checkbox_if_output()
            self.update_custom_actions()
            notify_tray()
        else:
            self.comp_manager.restore_state(ACTION_DOWNGRADE)
            self._show_console_errors()
            if self._can_notify_user():
                util.notify_user(self.i18n['notification.downgrade.failed'])

    def begin_show_info(self, pkg: dict):
        self._begin_action(self.i18n['manage_window.status.info'], action_id=ACTION_INFO)
        self.comp_manager.disable_visible()
        self.thread_show_info.pkg = pkg
        self.thread_show_info.start()

    def _finish_show_info(self, pkg_info: dict):
        self._finish_action(action_id=ACTION_INFO)
        if pkg_info:
            if len(pkg_info) > 1:
                dialog_info = InfoDialog(pkg_info=pkg_info, icon_cache=self.icon_cache, i18n=self.i18n, can_open_url=self.can_open_urls)
                dialog_info.exec_()
            else:
                dialog.show_message(title=self.i18n['warning'].capitalize(), body=self.i18n['manage_window.info.no_info'].format(bold(pkg_info['__app__'].model.name)), type_=MessageType.WARNING)

    def begin_show_screenshots(self, pkg: PackageView):
        self._begin_action(action_label=self.i18n['manage_window.status.screenshots'].format(bold(pkg.model.name)), action_id=ACTION_SCREENSHOTS)
        self.comp_manager.disable_visible()
        self.thread_screenshots.pkg = pkg
        self.thread_screenshots.start()

    def _finish_show_screenshots(self, res: dict):
        self._finish_action(ACTION_SCREENSHOTS)
        if res.get('screenshots'):
            diag = ScreenshotsDialog(pkg=res['pkg'], http_client=self.http_client, icon_cache=self.icon_cache, logger=self.logger, i18n=self.i18n, screenshots=res['screenshots'])
            diag.exec_()
        else:
            dialog.show_message(title=self.i18n['error'], body=self.i18n['popup.screenshots.no_screenshot.body'].format(bold(res['pkg'].model.name)), type_=MessageType.ERROR)

    def begin_show_history(self, pkg: PackageView):
        self._begin_action(self.i18n['manage_window.status.history'], action_id=ACTION_HISTORY)
        self.comp_manager.disable_visible()
        self.thread_show_history.pkg = pkg
        self.thread_show_history.start()

    def _finish_show_history(self, res: dict):
        self._finish_action(ACTION_HISTORY)
        if res.get('error'):
            self._handle_console_option(True)
            self.textarea_details.appendPlainText(res['error'])
            self.check_details.setChecked(True)
        elif not res['history'].history:
            dialog.show_message(title=self.i18n['action.history.no_history.title'], body=self.i18n['action.history.no_history.body'].format(bold(res['history'].pkg.name)), type_=MessageType.WARNING)
        else:
            dialog_history = HistoryDialog(res['history'], self.icon_cache, self.i18n)
            dialog_history.exec_()

    def search(self):
        word = self.search_bar.text().strip()
        if word:
            self.table_apps.stop_file_downloader()
            self._handle_console(False)
            self.filter_updates = False
            self.filter_installed = False
            label = f"{self.i18n['manage_window.status.searching']} {(word if word else '')}"
            self._begin_action(action_label=label, action_id=ACTION_SEARCH)
            self.comp_manager.set_components_visible(False)
            self.searched_term = word
            self.thread_search.word = word
            self.thread_search.start()

    def _finish_search(self, res: dict):
        self._finish_action()
        self.search_performed = True
        if not res['error']:
            self.comp_manager.set_group_visible(GROUP_VIEW_SEARCH, True)
            self.update_pkgs(res['pkgs_found'], as_installed=False, ignore_updates=True)
            self._set_lower_buttons_visible(True)
            self._update_bts_installed_and_suggestions()
            self._hide_filters_no_packages()
            self._reorganize()
        else:
            self.comp_manager.restore_state(ACTION_SEARCH)
            dialog.show_message(title=self.i18n['warning'].capitalize(), body=self.i18n[res['error']], type_=MessageType.WARNING)

    def _ask_root_password(self, action: SoftwareAction, pkg: PackageView) -> Tuple[Optional[str], bool]:
        pwd = None
        requires_root = self.manager.requires_root(action, pkg.model)
        if not user.is_root() and requires_root:
            valid, pwd = RootDialog.ask_password(self.context, i18n=self.i18n, comp_manager=self.comp_manager)
            if not valid:
                return (pwd, False)
        return (pwd, True)

    def install(self, pkg: PackageView):
        pwd, proceed = self._ask_root_password(SoftwareAction.INSTALL, pkg)
        if not proceed:
            return
        self._begin_action('{} {}'.format(self.i18n['manage_window.status.installing'], pkg.model.name), action_id=ACTION_INSTALL)
        self.comp_manager.set_groups_visible(False, GROUP_UPPER_BAR, GROUP_LOWER_BTS)
        self._handle_console_option(True)
        self.thread_install.pkg = pkg
        self.thread_install.root_pwd = pwd
        self.thread_install.start()

    def _write_operation_logs(self, type_: str, pkg: Optional[PackageView]=None, custom_log_file: Optional[str]=None):
        console_output = self.textarea_details.toPlainText()
        if console_output:
            if custom_log_file:
                log_dir = os.path.dirname(custom_log_file)
                log_file = custom_log_file
            else:
                log_dir = f'{LOGS_DIR}/{type_}'
                if pkg:
                    log_dir = f'{log_dir}/{pkg.model.get_type()}/{pkg.model.name}'
                log_file = f'{log_dir}/{int(time.time())}.log'
            try:
                Path(log_dir).mkdir(parents=True, exist_ok=True)
            except OSError:
                self.logger.error(f"Could not create the operation log directory '{log_dir}'")
                return
            try:
                with open(log_file, 'w+') as f:
                    f.write(console_output)
            except OSError:
                self.logger.error(f"Could not write the operation log to file '{log_file}'")
                return
            log_msg = '\n* ' + self.i18n['console.operation_log'].format(path=f'"{log_file}"')
            self.textarea_details.appendPlainText(log_msg)

    def _finish_install(self, res: dict):
        self._finish_action(action_id=ACTION_INSTALL)
        self._write_operation_logs('install', res['pkg'])
        if res['success']:
            if self._can_notify_user():
                util.notify_user(msg='{} ({}) {}'.format(res['pkg'].model.name, res['pkg'].model.get_type(), self.i18n['installed']))
            models_updated = []
            for key in ('installed', 'removed'):
                if res.get(key):
                    models_updated.extend(res[key])
            if models_updated:
                installed_available_idxs = []
                for idx, available in enumerate(self.pkgs_available):
                    for pidx, model in enumerate(models_updated):
                        if available.model == model:
                            available.update_model(model)
                            if model.installed:
                                installed_available_idxs.append((idx, pidx, available))
                if installed_available_idxs:
                    installed_available_idxs.sort(key=operator.itemgetter(0))
                    for decrement, data in enumerate(installed_available_idxs):
                        del self.pkgs_available[data[0] - decrement]
                    installed_available_idxs.sort(key=operator.itemgetter(1))
                    for new_idx, data in enumerate(installed_available_idxs):
                        self.pkgs_available.insert(new_idx, data[2])
                screen_width = get_current_screen_geometry(self).width()
                for displayed in self.pkgs:
                    for model in models_updated:
                        if displayed.model == model:
                            self.table_apps.update_package(displayed, screen_width=screen_width, change_update_col=True)
                self.update_bt_upgrade()
            if res['removed'] and self.pkgs_installed:
                to_remove = []
                for idx, installed in enumerate(self.pkgs_installed):
                    for removed in res['removed']:
                        if installed.model == removed:
                            to_remove.append(idx)
                if to_remove:
                    to_remove.sort()
                    for decrement, idx in enumerate(to_remove):
                        del self.pkgs_installed[idx - decrement]
            if res['installed']:
                for idx, model in enumerate(res['installed']):
                    self.pkgs_installed.insert(idx, PackageView(model, self.i18n))
            self.update_custom_actions()
            self._update_installed_filter(installed_available=True, keep_state=True)
            self._update_index()
            self.table_apps.change_headers_policy(policy=QHeaderView.Stretch, maximized=self._maximized)
            self.table_apps.change_headers_policy(policy=QHeaderView.ResizeToContents, maximized=self._maximized)
            self._resize(accept_lower_width=False)
        else:
            self._show_console_errors()
            if self._can_notify_user():
                util.notify_user('{}: {}'.format(res['pkg'].model.name, self.i18n['notification.install.failed']))

    def begin_execute_custom_action(self, pkg: Optional[PackageView], action: CustomSoftwareAction):
        if pkg is None and action.requires_confirmation and (not ConfirmationDialog(title=self.i18n['confirmation'].capitalize(), body='<p>{}</p>'.format(self.i18n['custom_action.proceed_with'].capitalize().format(bold(self.i18n[action.i18n_label_key]))), icon=QIcon(action.icon_path) if action.icon_path else QIcon(resource.get_path('img/gekko-bauh.png')), i18n=self.i18n).ask()):
            return False
        pwd = None
        if not user.is_root() and action.requires_root:
            valid, pwd = RootDialog.ask_password(self.context, i18n=self.i18n, comp_manager=self.comp_manager)
            if not valid:
                return
        action_label = self.i18n[action.i18n_status_key]
        if pkg:
            if '{}' in action_label:
                action_label = action_label.format(pkg.model.name)
            else:
                action_label += f' {pkg.model.name}'
        if action.refresh:
            self.table_apps.stop_file_downloader()
        self._begin_action(action_label=action_label, action_id=ACTION_CUSTOM_ACTION)
        self.comp_manager.set_components_visible(False)
        self._handle_console_option(True)
        self.thread_custom_action.pkg = pkg
        self.thread_custom_action.root_pwd = pwd
        self.thread_custom_action.custom_action = action
        self.thread_custom_action.start()

    def _finish_execute_custom_action(self, res: dict):
        self._finish_action()
        if res['success']:
            if res['action'].refresh:
                self.comp_manager.remove_saved_state(ACTION_CUSTOM_ACTION)
                self.update_custom_actions()
                self.begin_refresh_packages(pkg_types={res['pkg'].model.__class__} if res['pkg'] else None)
            else:
                self.comp_manager.restore_state(ACTION_CUSTOM_ACTION)
            self._show_console_checkbox_if_output()
        else:
            self.comp_manager.restore_state(ACTION_CUSTOM_ACTION)
            self._show_console_errors()
            if res['error']:
                dialog.show_message(title=self.i18n['warning' if res['error_type'] == MessageType.WARNING else 'error'].capitalize(), body=self.i18n[res['error']], type_=res['error_type'])

    def _show_console_checkbox_if_output(self):
        if self.textarea_details.toPlainText():
            self.comp_manager.set_component_visible(CHECK_DETAILS, True)
        else:
            self.comp_manager.set_component_visible(CHECK_DETAILS, False)

    def begin_ignore_updates(self, pkg: PackageView):
        status_key = 'ignore_updates' if not pkg.model.is_update_ignored() else 'ignore_updates_reverse'
        self._begin_action(action_label=self.i18n['manage_window.status.{}'.format(status_key)].format(pkg.model.name), action_id=ACTION_IGNORE_UPDATES)
        self.comp_manager.disable_visible()
        self.thread_ignore_updates.pkg = pkg
        self.thread_ignore_updates.start()

    def finish_ignore_updates(self, res: dict):
        self._finish_action(action_id=ACTION_IGNORE_UPDATES)
        if res['success']:
            hide_package = commons.is_package_hidden(res['pkg'], self._gen_filters())
            if hide_package:
                idx_to_remove = None
                for pkg in self.pkgs:
                    if pkg == res['pkg']:
                        idx_to_remove = pkg.table_index
                        break
                if idx_to_remove is not None:
                    del self.pkgs[idx_to_remove]
                    self.table_apps.removeRow(idx_to_remove)
                    self._update_table_indexes()
                    self.update_bt_upgrade()
            else:
                screen_width = get_current_screen_geometry(self).width()
                for pkg in self.pkgs:
                    if pkg == res['pkg']:
                        pkg.update_model(res['pkg'].model)
                        self.table_apps.update_package(pkg, screen_width=screen_width, change_update_col=not any([self.search_performed, self.suggestions_requested]))
                        self.update_bt_upgrade()
                        break
            for pkg_list in (self.pkgs_available, self.pkgs_installed):
                if pkg_list:
                    for pkg in pkg_list:
                        if pkg == res['pkg']:
                            pkg.update_model(res['pkg'].model)
                            break
            self._add_pkg_categories(res['pkg'])
            self._update_index()
            dialog.show_message(title=self.i18n['success'].capitalize(), body=self.i18n['action.{}.success'.format(res['action'])].format(bold(res['pkg'].model.name)), type_=MessageType.INFO)
        else:
            dialog.show_message(title=self.i18n['fail'].capitalize(), body=self.i18n['action.{}.fail'.format(res['action'])].format(bold(res['pkg'].model.name)), type_=MessageType.ERROR)