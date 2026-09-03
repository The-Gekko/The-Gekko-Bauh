import logging
import shutil
from typing import List, Set, Optional, Dict, Any
from PyQt5.QtCore import QEvent, Qt, pyqtSignal, QRect
from PyQt5.QtGui import QIcon, QWindowStateChangeEvent, QCursor, QCloseEvent, QShowEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QHeaderView, QToolBar, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QComboBox, QApplication, QListView, QSizePolicy, QHBoxLayout, QFrame
from bauh.api.abstract.cache import MemoryCache
from bauh.api.abstract.context import ApplicationContext
from bauh.api.abstract.controller import SoftwareManager
from bauh.api.abstract.model import SoftwarePackage
from bauh.api.abstract.view import MessageType
from bauh.api.http import HttpClient
from bauh.context import set_theme
from bauh.view.qt import commons, qt_utils
from bauh.view.qt.apps_table import PackagesTable
from bauh.view.qt.commons import sum_updates_displayed
from bauh.view.qt.components import new_spacer, IconButton, QtComponentsManager, QSearchBar, QCustomToolbar
from bauh.view.qt.dialog import ConfirmationDialog
from bauh.view.qt.qt_utils import get_current_screen_geometry
from bauh.view.qt.thread import UpgradeSelected, RefreshApps, UninstallPackage, DowngradePackage, ShowPackageInfo, ShowPackageHistory, SearchPackages, InstallPackage, AnimateProgress, NotifyPackagesReady, FindSuggestions, ListWarnings, AsyncAction, LaunchPackage, ApplyFilters, ShowScreenshots, CustomAction, NotifyInstalledLoaded, IgnorePackageUpdates, SaveTheme, StartAsyncAction
from bauh.view.qt.view_index import add_to_index, new_package_index
from bauh.view.qt.view_model import PackageView, PackageViewStatus
from bauh.view.util.translation import I18n
from bauh.view.qt.window.constants import DISPLAY_NAME, BLOCKING_ACTIONS, SEARCH_BAR, BT_INSTALLED, BT_REFRESH, \
    BT_SUGGESTIONS, BT_UPGRADE, BT_MATUGEN, CHECK_INSTALLED, CHECK_UPDATES, CHECK_APPS, COMBO_TYPES, CHECK_VERIFIED, \
    COMBO_CATEGORIES, INP_NAME, CHECK_DETAILS, BT_SETTINGS, BT_CUSTOM_ACTIONS, BT_ABOUT, BT_THEMES, GROUP_FILTERS, \
    GROUP_VIEW_INSTALLED, GROUP_VIEW_SEARCH, GROUP_UPPER_BAR, GROUP_LOWER_BTS

from bauh.view.qt.window.mixins.actions import WindowActionsMixin
from bauh.view.qt.window.mixins.filters import WindowFiltersMixin
from bauh.view.qt.window.mixins.ui import WindowUIMixin

class ManageWindow(QWidget, WindowActionsMixin, WindowFiltersMixin, WindowUIMixin):
    signal_user_res = pyqtSignal(bool)
    signal_root_password = pyqtSignal(bool, str)
    signal_table_update = pyqtSignal()
    signal_stop_notifying = pyqtSignal()

    def __init__(self, i18n: I18n, icon_cache: MemoryCache, manager: SoftwareManager, config: dict, context: ApplicationContext, http_client: HttpClient, logger: logging.Logger, icon: QIcon, force_suggestions: bool=False):
        super(ManageWindow, self).__init__()
        self.setObjectName('manage_window')
        self.comp_manager = QtComponentsManager()
        self.i18n = i18n
        self.logger = logger
        self.manager = manager
        self.working = False  # restrict the number of threaded actions
        self.installed_loaded = False  # used to control the state when the interface is set to not load the apps on startup
        self.pkgs = []  # packages current loaded in the table
        self.pkgs_available = []  # all packages loaded in memory
        self.pkgs_installed = []  # cached installed packages
        self.pkg_idx: Optional[Dict[str, Any]] = None  # all packages available indexed by the available filters
        self.display_limit = config['ui']['table']['max_displayed']
        self.icon_cache = icon_cache
        self.config = config
        self.context = context
        self.http_client = http_client
        self.icon_app = icon
        self.setWindowIcon(self.icon_app)
        self.setWindowTitle(DISPLAY_NAME)
        
        custom_theme_config = self.config.get('custom_theme') or {}
        opacity = custom_theme_config.get('opacity', 100)
        self.setWindowOpacity(opacity / 100.0)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(6, 4, 6, 4)
        self.layout.setSpacing(3)
        self.setLayout(self.layout)
        self.toolbar_status = QToolBar()
        self.toolbar_status.setObjectName('toolbar_status')
        self.toolbar_status.addWidget(new_spacer())
        self.icon_status = QLabel()
        self.icon_status.setObjectName('icon_status')
        self.icon_status.setVisible(False)
        self.toolbar_status.addWidget(self.icon_status)
        self.label_status = QLabel()
        self.label_status.setObjectName('label_status')
        self.label_status.setText('')
        self.toolbar_status.addWidget(self.label_status)
        self.search_bar = QSearchBar(search_callback=self.search)
        self.search_bar.set_placeholder(i18n['window_manage.search_bar.placeholder'] + '...')
        self.search_bar.set_tooltip(i18n['window_manage.search_bar.tooltip'])
        self.search_bar.set_button_tooltip(i18n['window_manage.search_bar.button_tooltip'])
        self.comp_manager.register_component(SEARCH_BAR, self.search_bar, self.toolbar_status.addWidget(self.search_bar))
        self.toolbar_status.addWidget(new_spacer())
        self.layout.addWidget(self.toolbar_status)
        self.toolbar_filters = QWidget()
        self.toolbar_filters.setObjectName('table_filters')
        self.toolbar_filters.setLayout(QHBoxLayout())
        self.toolbar_filters.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.toolbar_filters.setContentsMargins(0, 0, 0, 0)
        self.check_updates = QCheckBox()
        self.check_updates.setObjectName('check_updates')
        self.check_updates.setCursor(QCursor(Qt.PointingHandCursor))
        self.check_updates.setText(self.i18n['updates'].capitalize())
        self.check_updates.stateChanged.connect(self._handle_updates_filter)
        self.check_updates.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.check_updates)
        self.comp_manager.register_component(CHECK_UPDATES, self.check_updates)
        self.check_installed = QCheckBox()
        self.check_installed.setObjectName('check_installed')
        self.check_installed.setCursor(QCursor(Qt.PointingHandCursor))
        self.check_installed.setText(self.i18n['manage_window.checkbox.only_installed'])
        self.check_installed.setChecked(False)
        self.check_installed.stateChanged.connect(self._handle_filter_only_installed)
        self.check_installed.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.check_installed)
        self.comp_manager.register_component(CHECK_INSTALLED, self.check_installed)
        self.check_apps = QCheckBox()
        self.check_apps.setObjectName('check_apps')
        self.check_apps.setCursor(QCursor(Qt.PointingHandCursor))
        self.check_apps.setText(self.i18n['manage_window.checkbox.only_apps'])
        self.check_apps.setChecked(True)
        self.check_apps.stateChanged.connect(self._handle_filter_only_apps)
        self.check_apps.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.check_apps)
        self.comp_manager.register_component(CHECK_APPS, self.check_apps)
        self.check_verified = QCheckBox()
        self.check_verified.setObjectName('check_verified')
        self.check_verified.setCursor(QCursor(Qt.PointingHandCursor))
        self.check_verified.setText(self.i18n['manage_window.checkbox.only_verified'])
        self.check_verified.setChecked(False)
        self.check_verified.stateChanged.connect(self._handle_filter_only_verified)
        self.check_verified.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.check_verified)
        self.comp_manager.register_component(CHECK_VERIFIED, self.check_verified)
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFrameShadow(QFrame.Sunken)
        self.toolbar_filters.layout().addWidget(sep1)
        self.any_type_filter = 'any'
        self.cache_type_filter_icons = {}
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.setObjectName('combo_types')
        self.combo_filter_type.setCursor(QCursor(Qt.PointingHandCursor))
        self.combo_filter_type.setView(QListView())
        self.combo_filter_type.view().setCursor(QCursor(Qt.PointingHandCursor))
        self.combo_filter_type.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_filter_type.setEditable(True)
        self.combo_filter_type.lineEdit().setReadOnly(True)
        self.combo_filter_type.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_filter_type.activated.connect(self._handle_type_filter)
        self.combo_filter_type.addItem('--- {} ---'.format(self.i18n['type'].capitalize()), self.any_type_filter)
        self.combo_filter_type.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.combo_filter_type)
        self.comp_manager.register_component(COMBO_TYPES, self.combo_filter_type)
        self.any_category_filter = 'any'
        self.combo_categories = QComboBox()
        self.combo_categories.setObjectName('combo_categories')
        self.combo_categories.setCursor(QCursor(Qt.PointingHandCursor))
        self.combo_categories.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_categories.view().setCursor(QCursor(Qt.PointingHandCursor))
        self.combo_categories.setEditable(True)
        self.combo_categories.lineEdit().setReadOnly(True)
        self.combo_categories.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_categories.activated.connect(self._handle_category_filter)
        self.combo_categories.sizePolicy().setRetainSizeWhenHidden(True)
        self.combo_categories.addItem('--- {} ---'.format(self.i18n['category'].capitalize()), self.any_category_filter)
        self.toolbar_filters.layout().addWidget(self.combo_categories)
        self.comp_manager.register_component(COMBO_CATEGORIES, self.combo_categories)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFrameShadow(QFrame.Sunken)
        self.toolbar_filters.layout().addWidget(sep2)
        self.input_name = QSearchBar(search_callback=self.begin_apply_filters)
        self.input_name.palette().swap(self.combo_categories.palette())
        self.input_name.setObjectName('name_filter')
        self.input_name.set_placeholder(self.i18n['manage_window.name_filter.placeholder'] + '...')
        self.input_name.set_tooltip(self.i18n['manage_window.name_filter.tooltip'])
        self.input_name.set_button_tooltip(self.i18n['manage_window.name_filter.button_tooltip'])
        self.input_name.sizePolicy().setRetainSizeWhenHidden(True)
        self.toolbar_filters.layout().addWidget(self.input_name)
        self.comp_manager.register_component(INP_NAME, self.input_name)
        self.toolbar_filters.layout().addWidget(new_spacer())
        toolbar_bts = []
        bt_inst = QPushButton()
        bt_inst.setObjectName('bt_installed')
        bt_inst.setProperty('root', 'true')
        bt_inst.setCursor(QCursor(Qt.PointingHandCursor))
        bt_inst.setToolTip(self.i18n['manage_window.bt.installed.tooltip'])
        bt_inst.setText(self.i18n['manage_window.bt.installed.text'].capitalize())
        bt_inst.clicked.connect(self._begin_loading_installed)
        bt_inst.sizePolicy().setRetainSizeWhenHidden(True)
        toolbar_bts.append(bt_inst)
        self.toolbar_filters.layout().addWidget(bt_inst)
        self.comp_manager.register_component(BT_INSTALLED, bt_inst)
        bt_ref = QPushButton()
        bt_ref.setObjectName('bt_refresh')
        bt_ref.setProperty('root', 'true')
        bt_ref.setCursor(QCursor(Qt.PointingHandCursor))
        bt_ref.setToolTip(i18n['manage_window.bt.refresh.tooltip'])
        bt_ref.setText(self.i18n['manage_window.bt.refresh.text'])
        bt_ref.clicked.connect(self.begin_refresh_packages)
        bt_ref.sizePolicy().setRetainSizeWhenHidden(True)
        toolbar_bts.append(bt_ref)
        self.toolbar_filters.layout().addWidget(bt_ref)
        self.comp_manager.register_component(BT_REFRESH, bt_ref)
        self.bt_upgrade = QPushButton()
        self.bt_upgrade.setProperty('root', 'true')
        self.bt_upgrade.setObjectName('bt_upgrade')
        self.bt_upgrade.setCursor(QCursor(Qt.PointingHandCursor))
        self.bt_upgrade.setToolTip(i18n['manage_window.bt.upgrade.tooltip'])
        self.bt_upgrade.setText(i18n['manage_window.bt.upgrade.text'])
        self.bt_upgrade.clicked.connect(self.upgrade_selected)
        self.bt_upgrade.sizePolicy().setRetainSizeWhenHidden(True)
        toolbar_bts.append(self.bt_upgrade)
        self.toolbar_filters.layout().addWidget(self.bt_upgrade)
        self.comp_manager.register_component(BT_UPGRADE, self.bt_upgrade)

        self.bt_matugen = QPushButton()
        self.bt_matugen.setObjectName('bt_matugen')
        self.bt_matugen.setProperty('root', 'true')
        self.bt_matugen.setCursor(QCursor(Qt.PointingHandCursor))
        self.bt_matugen.setToolTip(self.i18n.get('manage_window.bt.matugen.tip',
                                                 'Sync the dynamic Matugen theme with the current wallpaper'))
        self.bt_matugen.setText(self.i18n.get('manage_window.bt.matugen.text', 'Matugen'))
        # se usa un icono del tema del sistema (nunca un emoji) para no alterar el ancho calculado de la barra
        matugen_icon = QIcon.fromTheme('preferences-desktop-theme')
        if not matugen_icon.isNull():
            self.bt_matugen.setIcon(matugen_icon)
        self.bt_matugen.clicked.connect(self._handle_matugen_toggle)
        self.bt_matugen.sizePolicy().setRetainSizeWhenHidden(True)
        toolbar_bts.append(self.bt_matugen)
        self.toolbar_filters.layout().addWidget(self.bt_matugen)
        self.comp_manager.register_component(BT_MATUGEN, self.bt_matugen)
        # setting all buttons to the same size:
        bt_biggest_size = 0
        for bt in toolbar_bts:
            bt_width = bt.sizeHint().width()
            if bt_width > bt_biggest_size:
                bt_biggest_size = bt_width
        for bt in toolbar_bts:
            bt_width = bt.sizeHint().width()
            if bt_biggest_size > bt_width:
                bt.setFixedWidth(bt_biggest_size)
        self.layout.addWidget(self.toolbar_filters)
        self.table_container = QWidget()
        self.table_container.setObjectName('table_container')
        self.table_container.setContentsMargins(0, 0, 0, 0)
        self.table_container.setLayout(QVBoxLayout())
        self.table_container.layout().setContentsMargins(0, 0, 0, 0)
        self.table_apps = PackagesTable(parent=self, icon_cache=self.icon_cache, download_icons=bool(self.config['download']['icons']), logger=logger)
        self.table_apps.change_headers_policy()
        self.table_container.layout().addWidget(self.table_apps)
        self.layout.addWidget(self.table_container)
        self.toolbar_console = QWidget()
        self.toolbar_console.setObjectName('console_toolbar')
        self.toolbar_console.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.toolbar_console.setLayout(QHBoxLayout())
        self.toolbar_console.setContentsMargins(0, 0, 0, 0)
        self.check_details = QCheckBox()
        self.check_details.setObjectName('check_details')
        self.check_details.setCursor(QCursor(Qt.PointingHandCursor))
        self.check_details.setText(self.i18n['manage_window.checkbox.show_details'])
        self.check_details.stateChanged.connect(self._handle_console)
        self.toolbar_console.layout().addWidget(self.check_details)
        self.comp_manager.register_component(CHECK_DETAILS, self.check_details)
        self.toolbar_console.layout().addWidget(new_spacer())
        self.label_displayed = QLabel()
        self.label_displayed.setObjectName('apps_displayed')
        self.label_displayed.setCursor(QCursor(Qt.WhatsThisCursor))
        self.label_displayed.setToolTip(self.i18n['manage_window.label.apps_displayed.tip'])
        self.toolbar_console.layout().addWidget(self.label_displayed)
        self.label_displayed.hide()
        self.label_updates_count = QLabel()
        self.label_updates_count.setObjectName('updates_count')
        self.label_updates_count.setToolTip(self.i18n.get('manage_window.label.updates_count.tip', 'Available updates'))
        self.toolbar_console.layout().addWidget(self.label_updates_count)
        self.label_updates_count.hide()
        self.layout.addWidget(self.toolbar_console)
        self.textarea_details = QPlainTextEdit(self)
        self.textarea_details.setObjectName('textarea_details')
        self.textarea_details.setProperty('console', 'true')
        self.textarea_details.resize(self.table_apps.size())
        self.layout.addWidget(self.textarea_details)
        self.textarea_details.setVisible(False)
        self.textarea_details.setReadOnly(True)
        self.toolbar_substatus = QToolBar()
        self.toolbar_substatus.setObjectName('toolbar_substatus')
        self.toolbar_substatus.addWidget(new_spacer())
        self.label_substatus = QLabel()
        self.label_substatus.setObjectName('label_substatus')
        self.label_substatus.setCursor(QCursor(Qt.WaitCursor))
        self.toolbar_substatus.addWidget(self.label_substatus)
        self.toolbar_substatus.addWidget(new_spacer())
        self.layout.addWidget(self.toolbar_substatus)
        self._change_label_substatus('')
        self.thread_update = self._bind_async_action(UpgradeSelected(manager=self.manager, i18n=self.i18n, internet_checker=context.internet_checker, parent_widget=self), finished_call=self._finish_upgrade_selected)
        self.thread_refresh = self._bind_async_action(RefreshApps(i18n, self.manager), finished_call=self._finish_refresh_packages, only_finished=True)
        self.thread_uninstall = self._bind_async_action(UninstallPackage(self.manager, self.icon_cache, self.i18n), finished_call=self._finish_uninstall)
        self.thread_show_info = self._bind_async_action(ShowPackageInfo(i18n, self.manager), finished_call=self._finish_show_info)
        self.thread_show_history = self._bind_async_action(ShowPackageHistory(self.manager, self.i18n), finished_call=self._finish_show_history)
        self.thread_search = self._bind_async_action(SearchPackages(i18n, self.manager), finished_call=self._finish_search, only_finished=True)
        self.thread_downgrade = self._bind_async_action(DowngradePackage(self.manager, self.i18n), finished_call=self._finish_downgrade)
        self.thread_suggestions = self._bind_async_action(FindSuggestions(i18n=i18n, man=self.manager), finished_call=self._finish_load_suggestions, only_finished=True)
        self.thread_launch = self._bind_async_action(LaunchPackage(i18n, self.manager), finished_call=self._finish_launch_package, only_finished=False)
        self.thread_custom_action = self._bind_async_action(CustomAction(manager=self.manager, i18n=self.i18n), finished_call=self._finish_execute_custom_action)
        self.thread_screenshots = self._bind_async_action(ShowScreenshots(i18n, self.manager), finished_call=self._finish_show_screenshots)
        self.thread_apply_filters = ApplyFilters(i18n=i18n, logger=logger)
        self.thread_apply_filters.signal_finished.connect(self._finish_apply_filters)
        self.thread_apply_filters.signal_table.connect(self._update_table_and_upgrades)
        self.signal_table_update.connect(self.thread_apply_filters.stop_waiting)
        self.thread_install = InstallPackage(manager=self.manager, icon_cache=self.icon_cache, i18n=self.i18n)
        self._bind_async_action(self.thread_install, finished_call=self._finish_install)
        self.thread_animate_progress = AnimateProgress()
        self.thread_animate_progress.signal_change.connect(self._update_progress)
        self.thread_notify_pkgs_ready = NotifyPackagesReady()
        self.thread_notify_pkgs_ready.signal_changed.connect(self._update_package_data)
        self.thread_notify_pkgs_ready.signal_finished.connect(self._update_state_when_pkgs_ready)
        self.signal_stop_notifying.connect(self.thread_notify_pkgs_ready.stop_working)
        self.thread_ignore_updates = IgnorePackageUpdates(i18n=i18n, manager=self.manager)
        self._bind_async_action(self.thread_ignore_updates, finished_call=self.finish_ignore_updates)
        self.thread_reload = StartAsyncAction(delay_in_milis=5)
        self.thread_reload.signal_start.connect(self._reload)
        self.container_bottom = QWidget()
        self.container_bottom.setObjectName('container_bottom')
        self.container_bottom.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.container_bottom.setLayout(QHBoxLayout())
        self.container_bottom.layout().setContentsMargins(0, 0, 0, 0)
        self.container_bottom.layout().addWidget(new_spacer())
        self.load_suggestions = force_suggestions or bool(config['suggestions']['enabled'])
        self.suggestions_requested = False
        if self.load_suggestions:
            bt_sugs = IconButton(action=lambda: self.begin_load_suggestions(filter_installed=True), i18n=i18n, tooltip=self.i18n['manage_window.bt.suggestions.tooltip'])
            bt_sugs.setObjectName('suggestions')
            self.container_bottom.layout().addWidget(bt_sugs)
            self.comp_manager.register_component(BT_SUGGESTIONS, bt_sugs)
        bt_themes = IconButton(self.show_themes, i18n=self.i18n, tooltip=self.i18n['manage_window.bt_themes.tip'])
        bt_themes.setObjectName('themes')
        self.container_bottom.layout().addWidget(bt_themes)
        self.comp_manager.register_component(BT_THEMES, bt_themes)
        self.custom_actions = [a for a in manager.gen_custom_actions()]
        bt_custom_actions = IconButton(action=self.show_custom_actions, i18n=self.i18n, tooltip=self.i18n['manage_window.bt_custom_actions.tip'])
        bt_custom_actions.setObjectName('custom_actions')
        bt_custom_actions.setVisible(bool(self.custom_actions))
        self.container_bottom.layout().addWidget(bt_custom_actions)
        self.comp_manager.register_component(BT_CUSTOM_ACTIONS, bt_custom_actions)
        bt_settings = IconButton(action=self.show_settings, i18n=self.i18n, tooltip=self.i18n['manage_window.bt_settings.tooltip'])
        bt_settings.setObjectName('settings')
        self.container_bottom.layout().addWidget(bt_settings)
        self.comp_manager.register_component(BT_SETTINGS, bt_settings)
        bt_about = IconButton(action=self._show_about, i18n=self.i18n, tooltip=self.i18n['manage_window.settings.about'])
        bt_about.setObjectName('about')
        self.container_bottom.layout().addWidget(bt_about)
        self.comp_manager.register_component(BT_ABOUT, bt_about)
        self.layout.addWidget(self.container_bottom)
        self.container_progress = QCustomToolbar(spacing=0, policy_height=QSizePolicy.Fixed)
        self.container_progress.setObjectName('container_progress')
        self.container_progress.add_space()
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName('progress_manage')
        self.progress_bar.setCursor(QCursor(Qt.WaitCursor))
        self.progress_bar.setTextVisible(False)
        self.container_progress.add_widget(self.progress_bar)
        self.container_progress.add_space()
        self.layout.addWidget(self.container_progress)
        self.filter_only_apps = True
        self.filter_only_verified = False
        self.type_filter = self.any_type_filter
        self.category_filter = self.any_category_filter
        self.filter_updates = False
        self.filter_installed = False
        self._maximized = False
        self.progress_controll_enabled = True
        self.recent_uninstall = False
        self.types_changed = False
        self.dialog_about = None
        self.first_refresh = True
        self.thread_warnings = ListWarnings(man=manager, i18n=i18n)
        self.thread_warnings.signal_warnings.connect(self._show_warnings)
        self.settings_window = None
        self.search_performed = False
        self.thread_save_theme = SaveTheme(theme_key='')
        self.thread_load_installed = NotifyInstalledLoaded()
        self.thread_load_installed.signal_loaded.connect(self._finish_loading_installed)
        self._register_groups()
        self._screen_geometry: Optional[QRect] = None
        self.searched_term: Optional[str] = None  # last searched term
        self._can_open_urls: Optional[bool] = None  # whether URLs can be opened in the browser
        self.current_action_id: Optional[int] = None  # accion en curso (None cuando no hay ninguna)
        qt_utils.centralize(self)

    def _register_groups(self):
        common_filters = (CHECK_APPS, CHECK_VERIFIED, CHECK_UPDATES, COMBO_CATEGORIES, COMBO_TYPES, INP_NAME)
        self.comp_manager.register_group(GROUP_FILTERS, False, CHECK_INSTALLED, *common_filters)
        self.comp_manager.register_group(GROUP_VIEW_SEARCH, False, CHECK_INSTALLED, CHECK_VERIFIED, COMBO_CATEGORIES, COMBO_TYPES, INP_NAME, BT_INSTALLED, BT_SUGGESTIONS, BT_MATUGEN)
        self.comp_manager.register_group(GROUP_VIEW_INSTALLED, False, BT_REFRESH, BT_UPGRADE, BT_MATUGEN, *common_filters)
        self.comp_manager.register_group(GROUP_UPPER_BAR, False,
                                         CHECK_APPS, CHECK_VERIFIED, CHECK_UPDATES, CHECK_INSTALLED,  # checkboxes
                                         COMBO_CATEGORIES, COMBO_TYPES, INP_NAME,  # filters
                                         BT_INSTALLED, BT_SUGGESTIONS, BT_REFRESH, BT_UPGRADE, BT_MATUGEN)  # buttons
        self.comp_manager.register_group(GROUP_LOWER_BTS, False, BT_SUGGESTIONS, BT_THEMES, BT_CUSTOM_ACTIONS, BT_SETTINGS, BT_ABOUT)

    def update_custom_actions(self):
        self.custom_actions = [a for a in self.manager.gen_custom_actions()]

    def stop_notifying_package_states(self):
        if self.thread_notify_pkgs_ready.isRunning():
            self.signal_stop_notifying.emit()
            self.thread_notify_pkgs_ready.wait(1000)

    def _update_table_and_upgrades(self, packages_displayed: List[PackageView]):
        # generating a mocked info to keep compatibility with '_update_table' inputs.
        # 'not_installed' is only used for a quick check and does not require an exact number (only 0 or 1)
        info = {'pkgs_displayed': packages_displayed, 'not_installed': 1 if len(self.pkgs_installed) != len(self.pkgs_available) else 0}
        self._update_table(pkgs_info=info, signal=True)
        if self.pkgs:
            self._update_state_when_pkgs_ready()
            self.stop_notifying_package_states()
            self.thread_notify_pkgs_ready.pkgs = self.pkgs
            self.thread_notify_pkgs_ready.work = True
            self.thread_notify_pkgs_ready.start()

    def showEvent(self, event: Optional[QShowEvent]) -> None:
        super().showEvent(event)
        if not self.thread_warnings.isFinished():
            self.thread_warnings.start()
        self._screen_geometry = get_current_screen_geometry()
        self._update_size_limits()
        qt_utils.centralize(self)

    def verify_warnings(self):
        self.thread_warnings.start()

    def _begin_loading_installed(self):
        if self.installed_loaded:
            self.table_apps.stop_file_downloader()
            self.search_bar.clear()
            self.input_name.set_text('')
            self._begin_action(self.i18n['manage_window.status.installed'])
            self._handle_console_option(False)
            self.comp_manager.set_components_visible(False)
            self.suggestions_requested = False
            self.search_performed = False
            self.thread_load_installed.start()
        else:
            self.load_suggestions = False
            self.begin_refresh_packages()

    def _finish_loading_installed(self):
        self._finish_action()
        self.comp_manager.set_group_visible(GROUP_VIEW_INSTALLED, True)
        self.update_pkgs(new_pkgs=None, as_installed=True)
        self._hide_filters_no_packages()
        self._update_bts_installed_and_suggestions()
        self._set_lower_buttons_visible(True)
        self._reorganize()

    def _update_bts_installed_and_suggestions(self):
        available_types = len(self.manager.get_managed_types())
        self.comp_manager.set_component_visible(BT_INSTALLED, available_types > 0 and any([self.suggestions_requested, self.search_performed]))
        self.comp_manager.set_component_visible(BT_SUGGESTIONS, available_types > 0)

    def _update_state_when_pkgs_ready(self):
        if self.progress_bar.isVisible():
            return
        self._reload_categories()
        self._reorganize()

    def _update_package_data(self, idx: int):
        if self.table_apps.isEnabled() and self.pkgs is not None and (0 <= idx < len(self.pkgs)):
            pkg = self.pkgs[idx]
            pkg.status = PackageViewStatus.READY
            screen_width = get_current_screen_geometry(self).width()
            self.table_apps.update_package(pkg, screen_width=screen_width)

    def _reload_categories(self):
        categories = set()
        for p in self.pkgs_available:
            if p.model.categories:
                for c in p.model.categories:
                    if c:
                        cat = c.strip().lower()
                        if cat:
                            categories.add(cat)
        if categories:
            self._update_categories(categories, keep_selected=True)

    def _update_size_limits(self):
        self.setMinimumHeight(int(self._screen_geometry.height() * 0.5))
        self.setMinimumWidth(int(self._screen_geometry.width() * 0.5))
        self.setMaximumWidth(int(self._screen_geometry.width()))

    def changeEvent(self, e: QEvent):
        if isinstance(e, QWindowStateChangeEvent):
            self._maximized = self.isMaximized()
            self.table_apps.change_headers_policy(maximized=self._maximized)
            if not self._maximized:
                self._reorganize()
                self.adjustSize()

    def event(self, e: QEvent) -> bool:
        res = super(ManageWindow, self).event(e)
        if self.isVisible() and e.type() == 216:  # drop event
            current_geometry = get_current_screen_geometry()
            if current_geometry != self._screen_geometry:  # only if the display device has changed
                self._screen_geometry = current_geometry
                self._update_size_limits()
                self._reorganize()
                self.adjustSize()
        return res

    def _update_table_indexes(self):
        if self.pkgs:
            for new_idx, pkgv in enumerate(self.pkgs):  # updating the package indexes
                pkgv.table_index = new_idx

    def _update_index(self):
        if self.pkgs_available:
            idx = new_package_index()
            for pkgv in self.pkgs_available:
                add_to_index(pkgv, idx)
            self.pkg_idx = idx

    def _can_notify_user(self):
        return bool(self.config['system']['notifications']) and (self.isHidden() or self.isMinimized())

    def _update_table(self, pkgs_info: dict, signal: bool=False):
        self.pkgs = pkgs_info['pkgs_displayed']
        if pkgs_info['not_installed'] == 0:
            update_check = sum_updates_displayed(pkgs_info) > 0
        else:
            update_check = False
        self.table_apps.update_packages(self.pkgs, update_check_enabled=update_check)
        if not self._maximized:
            self.label_displayed.show()
            self.table_apps.change_headers_policy(QHeaderView.Stretch)
            self.table_apps.change_headers_policy()
            self._resize(accept_lower_width=len(self.pkgs) > 0)
            if len(self.pkgs) == 0 and len(self.pkgs_available) == 0:
                self.label_displayed.setText('')
            else:
                displayed = len(self.pkgs)
                total = len(self.pkgs_available)
                self.label_displayed.setText(f'{displayed} / {total}')
            updates_available = sum((1 for p in self.pkgs if p.model.update and (not p.model.is_update_ignored())))
            if updates_available > 0:
                self.label_updates_count.setText(f'⬆ {updates_available}')
                self.label_updates_count.setToolTip(self.i18n.get('manage_window.label.updates_count.tip', 'Available updates') + f': {updates_available}')
                self.label_updates_count.show()
            else:
                self.label_updates_count.hide()
        else:
            self.label_displayed.hide()
            self.label_updates_count.hide()
        if signal:
            self.signal_table_update.emit()

    def update_bt_upgrade(self, pkgs_info: dict=None):
        show_bt_upgrade = False
        if not any([self.suggestions_requested, self.search_performed]) and (not pkgs_info or pkgs_info['not_installed'] == 0):
            for pkg in pkgs_info['pkgs_displayed'] if pkgs_info else self.pkgs:
                if not pkg.model.is_update_ignored() and pkg.update_checked:
                    show_bt_upgrade = True
                    break
        self.comp_manager.set_component_visible(BT_UPGRADE, show_bt_upgrade)
        if show_bt_upgrade:
            self._reorganize()

    def change_update_state(self, pkgs_info: dict, trigger_filters: bool=True, keep_selected: bool=False):
        self.update_bt_upgrade(pkgs_info)
        if pkgs_info['updates'] > 0:
            if pkgs_info['not_installed'] == 0:
                if not self.comp_manager.is_visible(CHECK_UPDATES):
                    self.comp_manager.set_component_visible(CHECK_UPDATES, True)
                if not self.filter_updates and (not keep_selected):
                    self._change_checkbox(self.check_updates, True, 'filter_updates', trigger_filters)
            if pkgs_info['napp_updates'] > 0 and self.filter_only_apps and (not keep_selected):
                self._change_checkbox(self.check_apps, False, 'filter_only_apps', trigger_filters)
        else:
            if not keep_selected:
                self._change_checkbox(self.check_updates, False, 'filter_updates', trigger_filters)
            self.comp_manager.set_component_visible(CHECK_UPDATES, False)

    def update_pkgs(self, new_pkgs: Optional[List[SoftwarePackage]], as_installed: bool, types: Optional[Set[type]]=None, ignore_updates: bool=False, keep_filters: bool=False) -> bool:
        self.input_name.set_text('')
        pkgs_info = commons.new_pkgs_info()
        pkg_idx = new_package_index()
        filters = self._gen_filters(ignore_updates=ignore_updates)
        if new_pkgs is not None:
            old_installed = None
            if as_installed:
                old_installed = self.pkgs_installed
                self.pkgs_installed = []
            for pkg in new_pkgs:
                pkgv = PackageView(model=pkg, i18n=self.i18n)
                commons.update_info(pkgv, pkgs_info)
                add_to_index(pkgv, pkg_idx)
                commons.apply_filters(pkgv, filters, pkgs_info)
            if old_installed and types:
                for pkgv in old_installed:
                    if pkgv.model.__class__ not in types:
                        commons.update_info(pkgv, pkgs_info)
                        add_to_index(pkgv, pkg_idx)
                        commons.apply_filters(pkgv, filters, pkgs_info)
        else:
            for pkgv in self.pkgs_installed:
                commons.update_info(pkgv, pkgs_info)
                add_to_index(pkgv, pkg_idx)
                commons.apply_filters(pkgv, filters, pkgs_info)
        if pkgs_info['apps_count'] == 0 and (not self.suggestions_requested):
            if self.load_suggestions or self.types_changed:
                if as_installed:
                    self.pkgs_installed = pkgs_info['pkgs']
                self.begin_load_suggestions(filter_installed=True)
                self.load_suggestions = False
                return False
            elif not keep_filters:
                self._change_checkbox(self.check_apps, False, 'filter_only_apps', trigger=False)
                self.check_apps.setCheckable(False)
        elif not keep_filters:
            self.check_apps.setCheckable(True)
            self._change_checkbox(self.check_apps, True, 'filter_only_apps', trigger=False)
        self._update_verified_filter(verified_available=pkgs_info['verified'] > 0, keep_state=keep_filters)
        self.change_update_state(pkgs_info=pkgs_info, trigger_filters=False, keep_selected=keep_filters and bool(pkgs_info['pkgs_displayed']))
        self._update_categories(pkgs_info['categories'], keep_selected=keep_filters and bool(pkgs_info['pkgs_displayed']))
        self._update_type_filters(pkgs_info['available_types'], keep_selected=keep_filters and bool(pkgs_info['pkgs_displayed']))
        self._apply_filters(pkgs_info, ignore_updates=ignore_updates)
        self.change_update_state(pkgs_info=pkgs_info, trigger_filters=False, keep_selected=keep_filters and bool(pkgs_info['pkgs_displayed']))
        self.pkgs_available = pkgs_info['pkgs']
        self.pkg_idx = pkg_idx
        if as_installed:
            self.pkgs_installed = pkgs_info['pkgs']
        self.pkgs = pkgs_info['pkgs_displayed']
        self._update_installed_filter(installed_available=pkgs_info['installed'] > 0, keep_state=keep_filters, hide=as_installed)
        self._update_table(pkgs_info=pkgs_info)
        if new_pkgs:
            self.stop_notifying_package_states()
            self.thread_notify_pkgs_ready.work = True
            self.thread_notify_pkgs_ready.pkgs = self.pkgs
            self.thread_notify_pkgs_ready.start()
        self._resize(accept_lower_width=bool(self.pkgs_installed))
        if not self.installed_loaded and as_installed:
            self.installed_loaded = True
        return True

    def _add_pkg_categories(self, pkg: PackageView):
        if pkg.model.categories:
            pkg_categories = {c.strip().lower() for c in pkg.model.categories if c and c.strip()}
            if pkg_categories:
                current_categories = self._get_current_categories()
                if current_categories:
                    pkg_categories = {c.strip().lower() for c in pkg.model.categories if c}
                    if pkg_categories:
                        categories_to_add = {c for c in pkg_categories if c and c not in current_categories}
                        if categories_to_add:
                            for cat in categories_to_add:
                                self._add_category(cat)
                else:
                    self._update_categories(pkg_categories)

    def reload(self):
        self.thread_reload.start()

    def _reload(self):
        self.update_custom_actions()
        self.verify_warnings()
        self.types_changed = True
        self.begin_refresh_packages()

    def _blocking_threads(self) -> List[AsyncAction]:
        """Devuelve los hilos de accion (instalar/desinstalar/actualizar/...) que siguen vivos."""
        threads = (self.thread_update, self.thread_install, self.thread_uninstall, self.thread_downgrade,
                   self.thread_custom_action)
        return [t for t in threads if t is not None and t.isRunning()]

    def is_transaction_running(self) -> bool:
        """Indica si hay una transaccion de paquetes en curso (proceso privilegiado en marcha)."""
        return self.current_action_id in BLOCKING_ACTIONS or bool(self._blocking_threads())

    def _stop_action_threads(self, timeout: int = 5000) -> None:
        """Pide la parada de los hilos de accion vivos y los espera con un limite de tiempo."""
        running = self._blocking_threads()

        for thread in running:
            thread.stop = True
            thread.wait_confirmation = False
            thread.requestInterruption()

        for thread in running:
            if not thread.wait(timeout):
                self.logger.warning(f"The action thread '{thread.__class__.__name__}' did not stop within "
                                    f"{timeout} milliseconds")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_transaction_running():
            confirmed = ConfirmationDialog(title=self.i18n['manage_window.close.transaction.title'],
                                           body=f"<p>{self.i18n['manage_window.close.transaction.body']}</p>",
                                           i18n=self.i18n,
                                           confirmation_icon_type=MessageType.WARNING).ask()

            if not confirmed:
                event.ignore()
                return

            self._stop_action_threads()

        # needs to be stopped to avoid a Qt exception/crash
        self.table_apps.stop_file_downloader(wait=True)
        self.stop_notifying_package_states()
        event.accept()

    @property
    def can_open_urls(self) -> bool:
        if self._can_open_urls is None:
            self._can_open_urls = shutil.which('xdg-open')
        return self._can_open_urls

    def _handle_matugen_toggle(self):
        """Aplica el tema dinamico Matugen y lo persiste con el mismo mecanismo que el menu de temas."""
        theme_key = 'matugen'

        try:
            set_theme(theme_key=theme_key, app=QApplication.instance(), logger=self.logger, app_config=self.config)
        except Exception:
            self.logger.warning(f"Could not apply the '{theme_key}' theme", exc_info=True)
            return

        self.config['ui']['theme'] = theme_key
        self.thread_save_theme.theme_key = theme_key
        self.thread_save_theme.start()