from typing import Set, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from bauh.view.qt.window.constants import ACTION_APPLY_FILTERS, CHECK_INSTALLED, CHECK_VERIFIED, COMBO_TYPES, \
    COMBO_CATEGORIES, INP_NAME, GROUP_FILTERS, GROUP_UPPER_BAR, GROUP_LOWER_BTS
from bauh.view.qt import commons
from bauh.view.qt.commons import PackageFilters

class WindowFiltersMixin:
    """Filtros de la tabla de paquetes de la ventana principal.

    Contrato con la clase anfitriona (ManageWindow), que debe definir:
      - atributos de estado: 'i18n', 'display_limit', 'pkgs', 'pkgs_available', 'pkgs_installed',
        'pkg_idx', 'searched_term', 'search_performed', 'filter_updates', 'filter_installed',
        'filter_only_apps', 'filter_only_verified', 'category_filter', 'type_filter',
        'any_category_filter', 'any_type_filter', 'cache_type_filter_icons'
      - widgets: 'check_installed', 'check_verified', 'combo_categories', 'combo_filter_type', 'input_name'
      - colaboradores: 'comp_manager' (QtComponentsManager), 'thread_apply_filters' (ApplyFilters)
      - metodos: '_begin_action', '_finish_action', '_change_checkbox', '_resize', 'update_bt_upgrade',
        'stop_notifying_package_states'
    """

    def begin_apply_filters(self):
        self.stop_notifying_package_states()
        self._begin_action(action_label=self.i18n['manage_window.status.filtering'], action_id=ACTION_APPLY_FILTERS)
        self.comp_manager.disable_visible_from_groups(GROUP_UPPER_BAR, GROUP_LOWER_BTS)
        self.comp_manager.set_component_read_only(INP_NAME, True)
        self.thread_apply_filters.pkgs = self.pkgs_available
        self.thread_apply_filters.index = self.pkg_idx
        self.thread_apply_filters.filters = self._gen_filters()
        self.thread_apply_filters.start()
        self.setFocus(Qt.NoFocusReason)

    def _finish_apply_filters(self):
        self._finish_action(ACTION_APPLY_FILTERS)
        self.update_bt_upgrade()
        self._resize()

    def _hide_filters_no_packages(self):
        if not self.pkgs:
            self.comp_manager.set_group_visible(GROUP_FILTERS, False)

    def _handle_updates_filter(self, status: int):
        self.filter_updates = status == 2
        self.begin_apply_filters()

    def _handle_filter_only_apps(self, status: int):
        self.filter_only_apps = status == 2
        self.begin_apply_filters()

    def _handle_filter_only_verified(self, status: int):
        self.filter_only_verified = status == 2
        self.begin_apply_filters()

    def _handle_filter_only_installed(self, status: int):
        self.filter_installed = status == 2
        self.begin_apply_filters()

    def _handle_type_filter(self, idx: int):
        self.type_filter = self.combo_filter_type.itemData(idx)
        self.combo_filter_type.adjustSize()
        self.begin_apply_filters()

    def _handle_category_filter(self, idx: int):
        self.category_filter = self.combo_categories.itemData(idx)
        self.begin_apply_filters()

    def _gen_filters(self, ignore_updates: bool=False) -> PackageFilters:
        return PackageFilters(category=self.category_filter, display_limit=0 if self.filter_updates else self.display_limit, name=self.input_name.text().strip(), only_apps=False if self.search_performed else self.filter_only_apps, only_verified=self.filter_only_verified, only_updates=False if ignore_updates else self.filter_updates, only_installed=self.filter_installed, search=self.searched_term, type=self.type_filter)

    def _update_installed_filter(self, keep_state: bool=True, hide: bool=False, installed_available: Optional[bool]=None):
        if installed_available is not None:
            has_installed = installed_available
        elif self.pkgs_available == self.pkgs_installed:
            has_installed = False
        else:
            has_installed = False
            if self.pkgs_available:
                for p in self.pkgs_available:
                    if p.model.installed:
                        has_installed = True
                        break
        if not keep_state or not has_installed:
            self._change_checkbox(self.check_installed, False, 'filter_installed', trigger=False)
        if hide:
            self.comp_manager.set_component_visible(CHECK_INSTALLED, False)
        else:
            self.comp_manager.set_component_visible(CHECK_INSTALLED, has_installed)

    def _update_verified_filter(self, keep_state: bool=True, verified_available: Optional[bool]=None):
        if verified_available is not None:
            has_verified = verified_available
        else:
            has_verified = False
            if self.pkgs_available:
                has_verified = next((True for p in self.pkgs_available if p.model.is_trustable()), False)
        if not keep_state or not has_verified:
            self._change_checkbox(self.check_verified, False, 'filter_only_verified', trigger=False)
        self.comp_manager.set_component_visible(CHECK_VERIFIED, has_verified)

    def _apply_filters(self, pkgs_info: dict, ignore_updates: bool):
        pkgs_info['pkgs_displayed'] = []
        filters = self._gen_filters(ignore_updates=ignore_updates)
        for pkgv in pkgs_info['pkgs']:
            commons.apply_filters(pkgv, filters, pkgs_info)

    def _clean_combo_types(self):
        if self.combo_filter_type.count() > 1:
            for _ in range(self.combo_filter_type.count() - 1):
                self.combo_filter_type.removeItem(1)

    def _update_type_filters(self, available_types: dict=None, keep_selected: bool=False):
        if available_types is None:
            self.comp_manager.set_component_visible(COMBO_TYPES, self.combo_filter_type.count() > 2)
        else:
            keeping_selected = keep_selected and available_types and (self.type_filter in available_types)
            if not keeping_selected:
                self.type_filter = self.any_type_filter
                if not available_types:
                    self._clean_combo_types()
            if available_types:
                self._clean_combo_types()
                sel_type = -1
                for idx, item in enumerate(available_types.items()):
                    app_type, icon_path, label = (item[0], item[1]['icon'], item[1]['label'])
                    icon = self.cache_type_filter_icons.get(app_type)
                    if not icon:
                        icon = QIcon(icon_path)
                        self.cache_type_filter_icons[app_type] = icon
                    self.combo_filter_type.addItem(icon, label, app_type)
                    if keeping_selected and app_type == self.type_filter:
                        sel_type = idx + 1
                self.combo_filter_type.blockSignals(True)
                self.combo_filter_type.setCurrentIndex(sel_type if sel_type > -1 else 0)
                self.combo_filter_type.blockSignals(False)
                self.comp_manager.set_component_visible(COMBO_TYPES, len(available_types) > 1)
            else:
                self.comp_manager.set_component_visible(COMBO_TYPES, False)

    def _update_categories(self, categories: Set[str]=None, keep_selected: bool=False):
        if categories is None:
            self.comp_manager.set_component_visible(COMBO_CATEGORIES, self.combo_categories.count() > 1)
        else:
            keeping_selected = keep_selected and categories and (self.category_filter in categories)
            if not keeping_selected:
                self.category_filter = self.any_category_filter
            if categories:
                if self.combo_categories.count() > 1:
                    for _ in range(self.combo_categories.count() - 1):
                        self.combo_categories.removeItem(1)
                selected_cat = -1
                cat_list = list(categories)
                cat_list.sort()
                for idx, c in enumerate(cat_list):
                    self._add_category(c)
                    if keeping_selected and c == self.category_filter:
                        selected_cat = idx + 1
                self.combo_categories.blockSignals(True)
                self.combo_categories.setCurrentIndex(selected_cat if selected_cat > -1 else 0)
                self.combo_categories.blockSignals(False)
                self.comp_manager.set_component_visible(COMBO_CATEGORIES, True)
            else:
                self.comp_manager.set_component_visible(COMBO_CATEGORIES, False)

    def _add_category(self, category: str):
        i18n_cat = self.i18n.get('category.{}'.format(category), self.i18n.get(category, category))
        self.combo_categories.addItem(i18n_cat.capitalize(), category)

    def _get_current_categories(self) -> Set[str]:
        if self.combo_categories.count() > 1:
            return {self.combo_categories.itemData(idx) for idx in range(self.combo_categories.count()) if idx > 0}