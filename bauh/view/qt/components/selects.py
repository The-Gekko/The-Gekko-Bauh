from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QGroupBox, QGridLayout, QWidget, \
    QLabel, QSizePolicy, QHBoxLayout
from bauh.api.abstract.view import SingleSelectComponent, MultipleSelectComponent
from .buttons import CheckboxQt, RadioButtonQt


class FormRadioSelectQt(QWidget):

    def __init__(self, model: SingleSelectComponent, parent: QWidget = None):
        super(FormRadioSelectQt, self).__init__(parent=parent)
        self.model = model
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self.setProperty('opts', str(len(self.model.options) if self.model.options else 0))

        if model.id:
            self.setObjectName(model.id)

        if model.max_width and model.max_width > 0:
            self.setMaximumWidth(int(model.max_width))

        grid = QGridLayout()
        self.setLayout(grid)

        line, col = 0, 0
        for op in model.options:
            comp = RadioButtonQt(op, model)
            comp.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            comp.setText(op.label)
            comp.setToolTip(op.tooltip)

            if model.value and model.value == op:
                self.value = comp
                comp.setChecked(True)

            grid.addWidget(comp, line, col)

            if col + 1 == self.model.max_per_line:
                line += 1
                col = 0
            else:
                col += 1

        if model.max_width is not None and model.max_width <= 0:
            self.setMaximumWidth(int(self.sizeHint().width()))


class RadioSelectQt(QGroupBox):

    def __init__(self, model: SingleSelectComponent):
        super(RadioSelectQt, self).__init__(model.label + ' :' if model.label else None)

        if model.id:
            self.setObjectName(model.id)

        if not model.label:
            self.setProperty('no_label', 'true')

        self.model = model

        grid = QGridLayout()
        self.setLayout(grid)

        self.setProperty('opts', str(len(model.options)) if model.options else '0')

        line, col = 0, 0
        for op in model.options:
            comp = RadioButtonQt(op, model)
            comp.setText(op.label)
            comp.setToolTip(op.tooltip)

            if model.value and model.value == op:
                self.value = comp
                comp.setChecked(True)

            grid.addWidget(comp, line, col)

            if col + 1 == self.model.max_per_line:
                line += 1
                col = 0
            else:
                col += 1


class MultipleSelectQt(QGroupBox):

    def __init__(self, model: MultipleSelectComponent, callback):
        super(MultipleSelectQt, self).__init__(model.label if model.label else None)
        self.model = model
        self._layout = QGridLayout()
        self.setLayout(self._layout)

        if model.min_width and model.min_width > 0:
            self.setMinimumWidth(int(model.min_width))

        if model.max_width and model.max_width > 0:
            self.setMaximumWidth(int(model.max_width))

        if model.max_height and model.max_height > 0:
            self.setMaximumHeight(int(model.max_height))

        if model.label:
            line = 1
            pre_label = QLabel()
            self.layout().addWidget(pre_label, 0, 1)
        else:
            line = 0

        col = 0

        for op in model.options:
            comp = CheckboxQt(op, model, callback)

            if model.values and op in model.values:
                self.value = comp
                comp.setChecked(True)

            widget = QWidget()
            widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
            widget.setLayout(QHBoxLayout())
            widget.layout().addWidget(comp)

            if model.opt_max_width and model.opt_max_width > 0:
                widget.setMinimumWidth(int(model.opt_max_width))

            if op.tooltip:
                help_icon = QLabel()

                if op.extra_properties and op.extra_properties.get('warning') == 'true':
                    help_icon.setProperty('warning_icon', 'true')
                else:
                    help_icon.setProperty('help_icon', 'true')

                help_icon.setCursor(QCursor(Qt.WhatsThisCursor))
                help_icon.setToolTip(op.tooltip)
                widget.layout().addWidget(help_icon)

            self._layout.addWidget(widget, line, col)

            if col + 1 == self.model.max_per_line:
                line += 1
                col = 0
            else:
                col += 1

        if model.label:
            pos_label = QLabel()
            self.layout().addWidget(pos_label, line + 1, 1)

        if model.id:
            self.setObjectName(model.id)


class FormMultipleSelectQt(QWidget):

    def __init__(self, model: MultipleSelectComponent, parent: QWidget = None):
        super(FormMultipleSelectQt, self).__init__(parent=parent)
        self.model = model
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        if model.min_width and model.min_width > 0:
            self.setMinimumWidth(int(model.min_width))

        if model.max_width and model.max_width > 0:
            self.setMaximumWidth(int(model.max_width))

        if model.max_height and model.max_height > 0:
            self.setMaximumHeight(int(model.max_height))

        self._layout = QGridLayout()
        self.setLayout(self._layout)

        if model.label:
            line = 1
            self._layout.addWidget(QLabel(), 0, 1)
        else:
            line = 0

        col = 0

        for op in model.options:
            comp = CheckboxQt(op, model, None)

            if model.values and op in model.values:
                self.value = comp
                comp.setChecked(True)

            widget = QWidget()
            widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
            widget.setLayout(QHBoxLayout())
            widget.layout().addWidget(comp)

            if model.opt_max_width and model.opt_max_width > 0:
                widget.setMinimumWidth(int(model.opt_max_width))

            if op.tooltip:
                help_icon = QLabel()

                if op.extra_properties and op.extra_properties.get('warning') == 'true':
                    help_icon.setProperty('warning_icon', 'true')
                else:
                    help_icon.setProperty('help_icon', 'true')

                help_icon.setToolTip(op.tooltip)
                help_icon.setCursor(QCursor(Qt.WhatsThisCursor))
                widget.layout().addWidget(help_icon)

            self._layout.addWidget(widget, line, col)

            if col + 1 == self.model.max_per_line:
                line += 1
                col = 0
            else:
                col += 1

        if model.label:
            self.layout().addWidget(QLabel(), line + 1, 1)

        if model.id:
            self.setObjectName(model.id)

