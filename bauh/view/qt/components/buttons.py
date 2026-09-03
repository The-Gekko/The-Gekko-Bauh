from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QRadioButton, QCheckBox, QWidget, \
    QSizePolicy, QToolButton, QSlider, QWidgetAction, QPushButton, QMenu
from bauh.api.abstract.view import SingleSelectComponent, InputOption, MultipleSelectComponent, TwoStateButtonComponent
from bauh.view.util.translation import I18n


class RadioButtonQt(QRadioButton):

    def __init__(self, model: InputOption, model_parent: SingleSelectComponent):
        super(RadioButtonQt, self).__init__()
        self.model = model
        self.model_parent = model_parent
        self.toggled.connect(self._set_checked)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        if model_parent.id:
            self.setProperty('parent', model_parent.id)

        if model.icon_path:
            if model.icon_path.startswith('/'):
                self.setIcon(QIcon(model.icon_path))
            else:
                self.setIcon(QIcon.fromTheme(model.icon_path))

        if self.model.read_only:
            self.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.setFocusPolicy(Qt.NoFocus)

        if model.extra_properties:
            for name, val in model.extra_properties.items():
                self.setProperty(name, val)

    def _set_checked(self, checked: bool):
        if checked:
            self.model_parent.value = self.model


class CheckboxQt(QCheckBox):

    def __init__(self, model: InputOption, model_parent: MultipleSelectComponent, callback):
        super(CheckboxQt, self).__init__()
        self.model = model
        self.model_parent = model_parent
        self.stateChanged.connect(self._set_checked)
        self.callback = callback
        self.setText(model.label)
        self.setToolTip(model.tooltip)

        if model.icon_path:
            if model.icon_path.startswith('/'):
                self.setIcon(QIcon(model.icon_path))
            else:
                self.setIcon(QIcon.fromTheme(model.icon_path))

        if model.read_only:
            self.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.setFocusPolicy(Qt.NoFocus)
        else:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        if model.extra_properties:
            for name, val in model.extra_properties.items():
                self.setProperty(name, val)

    def _set_checked(self, state):
        checked = state == 2

        if checked:
            self.model_parent.values.add(self.model)
        else:
            if self.model in self.model_parent.values:
                self.model_parent.values.remove(self.model)

        if self.callback:
            self.callback(self.model, checked)


class TwoStateButtonQt(QSlider):

    def __init__(self, model: TwoStateButtonComponent):
        super(TwoStateButtonQt, self).__init__(Qt.Horizontal)
        self.model = model
        self.setMaximum(1)
        self.valueChanged.connect(self._change_state)

    def mousePressEvent(self, QMouseEvent):
        self.setValue(1 if self.value() == 0 else 0)

    def _change_state(self, state: int):
        self.model.state = bool(state)


class IconButton(QToolButton):

    def __init__(self, action, i18n: I18n, align: int = Qt.AlignCenter, tooltip: str = None, expanding: bool = False):
        super(IconButton, self).__init__()
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.clicked.connect(action)
        self.i18n = i18n
        self.default_tootip = tooltip
        self.setSizePolicy(QSizePolicy.Expanding if expanding else QSizePolicy.Minimum, QSizePolicy.Minimum)

        if tooltip:
            self.setToolTip(tooltip)

    def setEnabled(self, enabled):
        super(IconButton, self).setEnabled(enabled)

        if not enabled:
            self.setToolTip(self.i18n['icon_button.tooltip.disabled'])
        else:
            self.setToolTip(self.default_tootip)


class QCustomMenuAction(QWidgetAction):

    def __init__(self, parent: QWidget, label: Optional[str] = None, action=None, button_name: Optional[str] = None,
                 icon: Optional[QIcon] = None, tooltip: Optional[str] = None):
        super(QCustomMenuAction, self).__init__(parent)
        self.button = QPushButton()
        self.set_label(label)
        self._action = None
        self.set_action(action)
        self.set_button_name(button_name)
        self.set_icon(icon)
        self.setDefaultWidget(self.button)

        if tooltip:
            self.button.setToolTip(tooltip)

    def set_label(self, label: str):
        self.button.setText(label)

    def set_action(self, action):
        self._action = action
        self.button.clicked.connect(self._handle_action)

    def _handle_action(self):
        if self._action:
            self._action()

            if self.parent() and isinstance(self.parent(), QMenu):
                self.parent().close()

    def set_button_name(self, name: str):
        if name:
            self.button.setObjectName(name)

    def set_icon(self, icon: QIcon):
        if icon:
            self.button.setIcon(icon)

    def get_label(self) -> str:
        return self.button.text()

