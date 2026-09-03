from typing import Tuple, Dict, Optional, Set
from PyQt5.QtWidgets import QWidget, \
    QLineEdit, QAction


class QtComponentsManager:

    def __init__(self):
        self.components = {}
        self.groups = {}
        self.group_of_groups = {}
        self._saved_states = {}

    def register_component(self, component_id: int, instance: QWidget, action: Optional[QAction] = None):
        comp = (instance, action, {'v': True, 'e': True, 'r': False})
        self.components[component_id] = comp
        self._save_state(comp)

    def register_group(self, group_id: int, subgroups: bool, *ids: int):
        if not subgroups:
            self.groups[group_id] = {*ids}
        else:
            self.group_of_groups[group_id] = {*ids}

    def get_subgroups(self, root_group: int) -> Set[str]:
        return self.group_of_groups.get(root_group, set())

    def set_components_visible(self, visible: bool, *ids: int):
        if ids:
            for cid in ids:
                self.set_component_visible(cid, visible)
        else:
            for cid in self.components:
                self.set_component_visible(cid, visible)

    def set_component_visible(self, cid: int, visible: bool):
        comp = self.components.get(cid)
        if comp and self._is_visible(comp) != visible:
            self._save_state(comp)
            self._set_visible(comp, visible)

    def set_component_enabled(self, cid: int, enabled: bool):
        comp = self.components.get(cid)
        if comp and self._is_enabled(comp) != enabled:
            self._save_state(comp)
            self._set_enabled(comp, enabled)

    def set_component_read_only(self, cid: int, read_only: bool):
        comp = self.components.get(cid)
        if comp and self._supports_read_only(comp) and self._is_read_only(comp) != read_only:
            self._save_state(comp)
            self._set_read_only(comp, read_only)

    def set_components_enabled(self, enabled: bool, *ids: int):
        if ids:
            for cid in ids:
                self.set_component_enabled(cid, enabled)
        else:
            for cid in self.components:
                self.set_component_enabled(cid, enabled)

    def restore_previous_states(self, *ids: int):
        if ids:
            for cid in ids:
                self.restore_previous_state(cid)
        else:
            for cid in self.components:
                self.restore_previous_state(cid)

    def restore_previous_group_state(self, group_id: int):
        ids = self.groups.get(group_id)

        if ids:
            self.restore_previous_states(*ids)

    def restore_previous_groups_states(self, *groups: int):
        if groups:
            for group in groups:
                self.restore_previous_group_state(group)

    def set_group_visible(self, group_id: int, visible: bool):
        ids = self.groups.get(group_id)

        if ids:
            self.set_components_visible(visible, *ids)

    def set_groups_visible(self, visible: bool, *groups: int):
        if groups:
            for group in groups:
                self.set_group_visible(group, visible)

    def set_group_enabled(self, group_id: int, enabled: bool):
        ids = self.groups.get(group_id)

        if ids:
            self.set_components_enabled(enabled, *ids)

    def restore_previous_state(self, cid: int):
        comp = self.components.get(cid)

        if comp:
            previous_state = {**comp[2]}
            self._restore_state(comp, previous_state)

    def _set_visible(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]], visible: bool):
        if comp[1]:
            comp[1].setVisible(visible)
        else:
            comp[0].setVisible(visible)

    def _set_enabled(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]], enabled: bool):
        comp[0].setEnabled(enabled)

    def _set_read_only(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]], read_only: bool):
        comp[0].setReadOnly(read_only)

    def _supports_read_only(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]]) -> bool:
        return isinstance(comp, QLineEdit)

    def is_visible(self, cid: int) -> bool:
        comp = self.components.get(cid)
        return self._is_visible(comp) if comp else False

    def _is_visible(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]]) -> bool:
        return comp[1].isVisible() if comp[1] else comp[0].isVisible()

    def _is_enabled(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]]) -> bool:
        return comp[0].isEnabled()

    def _is_read_only(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]]) -> bool:
        return comp[0].isReadOnly() if self._supports_read_only(comp) else False

    def _save_state(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]]):
        comp[2]['v'] = self._is_visible(comp)
        comp[2]['e'] = self._is_enabled(comp)
        comp[2]['r'] = self._is_read_only(comp)

    def list_visible_from_group(self, group_id: int) -> Set[str]:
        ids = self.groups.get(group_id)
        if ids:
            return {cid for cid in ids if self.is_visible(cid)}

    def disable_visible_from_groups(self, *groups):
        if groups:
            for group in groups:
                ids = self.list_visible_from_group(group)

                if ids:
                    self.set_components_enabled(False, *ids)

    def disable_visible(self):
        self.set_components_enabled(False, *{cid for cid in self.components if self.is_visible(cid)})

    def enable_visible(self):
        self.set_components_enabled(True, *{cid for cid in self.components if self.is_visible(cid)})

    def enable_visible_from_groups(self, *groups):
        if groups:
            for group in groups:
                ids = self.list_visible_from_group(group)

                if ids:
                    self.set_components_enabled(True, *ids)

    def save_state(self, cid: int, state_id: int):
        comp = self.components.get(cid)

        if comp:
            self._save_state(comp)
            states = self._saved_states.get(state_id)

            if states is None:
                states = {}
                self._saved_states[state_id] = states

            states[cid] = {**comp[2]}

    def save_states(self, state_id: int, *ids, only_visible: bool = False):
        for cid in (ids if ids else self.components):
            if not only_visible or self.is_visible(cid):
                self.save_state(cid, state_id)

    def save_group_state(self, group_id: int, state_id: int):
        ids = self.groups.get(group_id)

        if ids:
            self.save_states(state_id, *ids)

    def save_groups_states(self, state_id: int, *group_ids):
        if group_ids:
            for group_id in group_ids:
                self.save_group_state(group_id, state_id)

    def _restore_state(self, comp: Tuple[QWidget, Optional[QAction], Dict[str, bool]], state: Dict[str, bool]):
        self._save_state(comp)

        if state['v'] != self._is_visible(comp):
            self._set_visible(comp, state['v'])

        if state['e'] != self._is_enabled(comp):
            self._set_enabled(comp, state['e'])

        if state['r'] != self._is_read_only(comp):
            self._set_read_only(comp, state['r'])

    def restore_group_state(self, group_id: int, state_id: int):
        states = self._saved_states.get(state_id)

        if states:
            ids = self.groups.get(group_id)

            if ids:
                for cid in ids:
                    comp_state = states.get(cid)

                    if comp_state:
                        comp = self.components.get(cid)

                        if comp:
                            self._restore_state(comp, comp_state)

    def restore_groups_state(self, state_id: int, *group_ids):
        if group_ids:
            for group_id in group_ids:
                self.restore_group_state(group_id, state_id)

    def restore_state(self, state_id: int):
        state = self._saved_states.get(state_id)

        if state:
            for cid, cstate in state.items():
                comp = self.components.get(cid)

                if comp:
                    self._restore_state(comp, cstate)

            del self._saved_states[state_id]

    def clear_saved_states(self):
        self._saved_states.clear()

    def remove_saved_state(self, state_id: int):
        if state_id in self._saved_states:
            del self._saved_states[state_id]

