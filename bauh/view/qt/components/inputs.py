import os
from pathlib import Path
from typing import Tuple
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QIntValidator, QCursor, QFocusEvent
from PyQt5.QtWidgets import QGroupBox, QComboBox, QGridLayout, QWidget, \
    QLabel, QSizePolicy, QLineEdit, QHBoxLayout, QFormLayout, QFileDialog, QSpinBox, QPlainTextEdit, QPushButton, QColorDialog
from bauh.api.abstract.view import SingleSelectComponent, MultipleSelectComponent, SelectViewType, \
    TextInputComponent, FormComponent, FileChooserComponent, ViewComponent, TwoStateButtonComponent, TextComponent, RangeInputComponent, ViewObserver, TextInputType, \
    ViewComponentAlignment, ColorPickerComponent
from bauh.view.util.translation import I18n

def map_alignment(alignment: ViewComponentAlignment) -> Qt.AlignmentFlag:
    if alignment == ViewComponentAlignment.CENTER:
        return Qt.AlignCenter
    elif alignment == ViewComponentAlignment.LEFT:
        return Qt.AlignLeft
    elif alignment == ViewComponentAlignment.RIGHT:
        return Qt.AlignRight
    elif alignment == ViewComponentAlignment.BOTTOM:
        return Qt.AlignBottom
    elif alignment == ViewComponentAlignment.TOP:
        return Qt.AlignTop
    elif alignment == ViewComponentAlignment.HORIZONTAL_CENTER:
        return Qt.AlignHCenter
    elif alignment == ViewComponentAlignment.VERTICAL_CENTER:
        return Qt.AlignVCenter
    return Qt.AlignLeft

from .selects import FormMultipleSelectQt, FormRadioSelectQt
from .buttons import TwoStateButtonQt, IconButton


class FormQt(QGroupBox):

    def __init__(self, model: FormComponent, i18n: I18n):
        super(FormQt, self).__init__(model.label if model.label else '')
        self.model = model
        self.i18n = i18n
        self.setLayout(QFormLayout())

        if model.id:
            self.setObjectName(model.id)

        if model.min_width and model.min_width > 0:
            self.setMinimumWidth(model.min_width)

        if model.spaces:
            self.layout().addRow(QLabel(), QLabel())

        for idx, c in enumerate(model.components):
            if isinstance(c, TextInputComponent):
                label, field = self._new_text_input(c)
                self.layout().addRow(label, field)
            elif isinstance(c, SingleSelectComponent):
                label = self._new_label(c)
                form = FormComboBoxQt(c) if c.type == SelectViewType.COMBO else FormRadioSelectQt(c)
                field = self._wrap(form, c)
                self.layout().addRow(label, field)
            elif isinstance(c, RangeInputComponent):
                label = self._new_label(c)
                field = self._wrap(self._new_range_input(c), c)
                self.layout().addRow(label, field)
            elif isinstance(c, FileChooserComponent):
                label, field = self._new_file_chooser(c)
                self.layout().addRow(label, field)
            elif isinstance(c, FormComponent):
                label, field = None, FormQt(c, self.i18n)
                self.layout().addRow(field)
            elif isinstance(c, TwoStateButtonComponent):
                label, field = self._new_label(c), TwoStateButtonQt(c)
                self.layout().addRow(label, field)
            elif isinstance(c, MultipleSelectComponent):
                label, field = self._new_label(c), FormMultipleSelectQt(c)
                self.layout().addRow(label, field)
            elif isinstance(c, TextComponent):
                label, field = self._new_label(c), QWidget()
                self.layout().addRow(label, field)
            elif isinstance(c, RangeInputComponent):
                label, field = self._new_label(c), self._new_range_input(c)
                self.layout().addRow(label, field)
            elif isinstance(c, ColorPickerComponent):
                label, field = self._new_label(c), ColorPickerQt(c)
                self.layout().addRow(label, field)
            else:
                raise Exception('Unsupported component type {}'.format(c.__class__.__name__))

            if label:  # to prevent C++ wrap errors
                setattr(self, 'label_{}'.format(idx), label)

            if field:  # to prevent C++ wrap errors
                setattr(self, 'field_{}'.format(idx), field)

        if model.spaces:
            self.layout().addRow(QLabel(), QLabel())

    def _new_label(self, comp) -> QWidget:
        label = QWidget()
        label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        label.setLayout(QHBoxLayout())
        label_comp = QLabel()
        label.layout().addWidget(label_comp)

        if hasattr(comp, 'min_width') and comp.min_width is not None and comp.min_width > 0:
            label_comp.setMinimumWidth(comp.min_width)

        if hasattr(comp, 'size') and comp.size is not None:
            label_comp.setStyleSheet("QLabel { font-size: " + str(comp.size) + "px }")

        if hasattr(comp, 'get_label'):
            text = comp.get_label()
        else:
            attr = 'label' if hasattr(comp, 'label') else 'value'
            text = getattr(comp, attr)

        if text:
            if hasattr(comp, 'capitalize_label') and getattr(comp, 'capitalize_label'):
                label_comp.setText(text.capitalize())
            else:
                label_comp.setText(text)

            if comp.tooltip:
                label.layout().addWidget(self.gen_tip_icon(comp.tooltip))

        return label

    def gen_tip_icon(self, tip: str) -> QLabel:
        tip_icon = QLabel()
        tip_icon.setProperty('tip_icon', 'true')
        tip_icon.setToolTip(tip.strip())
        tip_icon.setCursor(QCursor(Qt.WhatsThisCursor))
        return tip_icon

    def _new_text_input(self, c: TextInputComponent) -> Tuple[QLabel, QLineEdit]:
        view = QLineEditObserver() if c.type == TextInputType.SINGLE_LINE else QPlainTextEditObserver()
        view.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

        if c.id:
            view.setObjectName(c.id)

        if c.min_width >= 0:
            view.setMinimumWidth(int(c.min_width))

        if c.min_height >= 0:
            view.setMinimumHeight(int(c.min_height))

        if c.only_int:
            view.setValidator(QIntValidator())

        if c.tooltip:
            view.setToolTip(c.tooltip)

        if c.placeholder:
            view.setPlaceholderText(c.placeholder)

        if c.value is not None:
            view.setText(str(c.value))
            view.setCursorPosition(0)

        if c.read_only:
            view.setEnabled(False)

        def update_model(text: str):
            c.set_value(val=text, caller=view)

        view.textChanged.connect(update_model)
        c.observers.append(view)

        label = QWidget()
        label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        label.setLayout(QHBoxLayout())

        label_component = QLabel()
        label.layout().addWidget(label_component)

        if label:
            label_component.setText(c.get_label())

            if c.tooltip:
                label.layout().addWidget(self.gen_tip_icon(c.tooltip))

        return label, self._wrap(view, c)

    def _new_range_input(self, model: RangeInputComponent) -> QSpinBox:
        spinner = QSpinBox()
        spinner.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        spinner.setCursor(QCursor(Qt.PointingHandCursor))
        spinner.setMinimum(model.min)
        spinner.setMaximum(model.max)
        spinner.setSingleStep(model.step)
        spinner.setValue(model.value if model.value is not None else model.min)

        if model.id:
            spinner.setObjectName(model.id)

        if model.tooltip:
            spinner.setToolTip(model.tooltip)

        def _update_value():
            model.value = spinner.value()

        spinner.valueChanged.connect(_update_value)
        return spinner

    def _wrap(self, comp: QWidget, model: ViewComponent) -> QWidget:
        field_container = QWidget()
        field_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        field_container.setLayout(QHBoxLayout())
        field_container.layout().setContentsMargins(0, 0, 0, 0)
        field_container.layout().setSpacing(0)
        field_container.layout().setAlignment(Qt.AlignLeft)
        field_container.setProperty('wrapper', 'true')
        field_container.setProperty('wrapped_type', comp.__class__.__name__)

        if model.id:
            field_container.setProperty('wrapped', model.id)

        if model.max_width and model.max_width > 0:
            field_container.setMaximumWidth(int(model.max_width))

        field_container.layout().addWidget(comp)
        return field_container

    def _new_file_chooser(self, c: FileChooserComponent) -> Tuple[QLabel, QLineEdit]:
        chooser = QLineEditObserver()
        chooser.setProperty('file_chooser', 'true')
        chooser.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        chooser.setReadOnly(True)

        if c.id:
            chooser.setObjectName(c.id)

        if c.max_width and c.max_width > 0:
            chooser.setMaximumWidth(int(c.max_width))

        if c.file_path:
            chooser.setText(c.file_path)
            chooser.setCursorPosition(0)

        c.observers.append(chooser)
        chooser.setPlaceholderText(self.i18n['view.components.file_chooser.placeholder'])

        def open_chooser(e):
            if c.allowed_extensions:
                sorted_exts = [e for e in c.allowed_extensions if e != '*']
                sorted_exts.sort()

                if '*' in c.allowed_extensions:
                    sorted_exts.append('*')

                exts = ';;'.join((f'*.{e}' for e in sorted_exts))
            else:
                exts = '{} (*);;'.format(self.i18n['all_files'].capitalize())

            if c.file_path and os.path.isfile(c.file_path):
                cur_path = c.file_path
            elif c.search_path and os.path.exists(c.search_path):
                cur_path = c.search_path
            else:
                cur_path = str(Path.home())

            if c.directory:
                opts = QFileDialog.DontUseNativeDialog
                opts |= QFileDialog.ShowDirsOnly
                file_path = QFileDialog.getExistingDirectory(self, self.i18n['file_chooser.title'], cur_path, options=opts)
            else:
                file_path, _ = QFileDialog.getOpenFileName(self, self.i18n['file_chooser.title'], cur_path, exts, options=QFileDialog.DontUseNativeDialog)

            if file_path:
                c.set_file_path(file_path)

            chooser.setCursorPosition(0)

        def clean_path():
            c.set_file_path(None)

        chooser.mousePressEvent = open_chooser

        label = self._new_label(c)
        wrapped = self._wrap(chooser, c)

        bt = IconButton(i18n=self.i18n['clean'].capitalize(), action=clean_path, tooltip=self.i18n['clean'].capitalize())
        bt.setObjectName('clean_field')

        wrapped.layout().addWidget(bt)
        return label, wrapped


class TextInputQt(QGroupBox):

    def __init__(self, model: TextInputComponent):
        super(TextInputQt, self).__init__()
        self.model = model
        self.setLayout(QGridLayout())

        if model.id:
            self.setObjectName(model.id)

        if self.model.max_width and self.model.max_width > 0:
            self.setMaximumWidth(int(self.model.max_width))

        self.text_input = QLineEditObserver() if model.type == TextInputType.SINGLE_LINE else QPlainTextEditObserver()

        if model.only_int:
            self.text_input.setValidator(QIntValidator())

        if model.placeholder:
            self.text_input.setPlaceholderText(model.placeholder)

        if model.min_width >= 0:
            self.text_input.setMinimumWidth(int(model.min_width))

        if model.min_height >= 0:
            self.text_input.setMinimumHeight(int(model.min_height))

        if model.tooltip:
            self.text_input.setToolTip(model.tooltip)

        if model.value is not None:
            self.text_input.setText(model.value)
            self.text_input.setCursorPosition(0)

        self.text_input.textChanged.connect(self._update_model)

        self.model.observers.append(self.text_input)
        self.layout().addWidget(self.text_input, 0, 1)

    def _update_model(self, *args):
        change = args[0] if args else self.text_input.toPlainText()
        self.model.set_value(val=change, caller=self)


class InputFilter(QLineEdit):

    # retardo (ms) entre la ultima tecla pulsada y la notificacion del cambio
    TYPING_DELAY = 300

    def __init__(self, on_key_press):
        super(InputFilter, self).__init__()
        self.on_key_press = on_key_press
        self.last_text = ''
        self.typing = QTimer()
        # 'single shot' evita un temporizador repetitivo que nunca se detiene durante toda la sesion
        self.typing.setSingleShot(True)
        self.typing.timeout.connect(self.notify_text_change)

    def notify_text_change(self):
        text = self.text().strip()

        if text != self.last_text:
            self.last_text = text
            self.on_key_press()

    def keyPressEvent(self, event):
        super(InputFilter, self).keyPressEvent(event)
        # cada tecla reinicia la cuenta: el filtro se aplica al dejar de escribir
        self.typing.start(self.TYPING_DELAY)

    def get_text(self):
        return self.last_text

    def setText(self, p_str):
        super(InputFilter, self).setText(p_str)
        self.last_text = p_str


class QCustomLineEdit(QLineEdit):

    def __init__(self, focus_in_callback, focus_out_callback, **kwargs):
        super(QCustomLineEdit, self).__init__(**kwargs)
        self.focus_in_callback = focus_in_callback
        self.focus_out_callback = focus_out_callback

    def focusInEvent(self, ev: QFocusEvent):
        super(QCustomLineEdit, self).focusInEvent(ev)
        if self.focus_in_callback:
            self.focus_in_callback()

    def focusOutEvent(self, ev: QFocusEvent):
        super(QCustomLineEdit, self).focusOutEvent(ev)
        if self.focus_out_callback:
            self.focus_out_callback()

        self.clearFocus()


class RangeInputQt(QGroupBox):

    def __init__(self, model: RangeInputComponent):
        super(RangeInputQt, self).__init__()
        self.model = model
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel(model.label.capitalize() + ' :' if model.label else ''), 0, 0)

        if self.model.max_width > 0:
            self.setMaximumWidth(int(self.model.max_width))

        self.spinner = QSpinBox()
        self.spinner.setCursor(QCursor(Qt.PointingHandCursor))
        self.spinner.setMinimum(model.min)
        self.spinner.setMaximum(model.max)
        self.spinner.setSingleStep(model.step)
        self.spinner.setValue(model.value if model.value is not None else model.min)

        if model.tooltip:
            self.spinner.setToolTip(model.tooltip)

        self.layout().addWidget(self.spinner, 0, 1)

        self.spinner.valueChanged.connect(self._update_value)

    def _update_value(self):
        self.model.value = self.spinner.value()


class ComboSelectQt(QGroupBox):

    def __init__(self, model: SingleSelectComponent):
        super(ComboSelectQt, self).__init__()
        self.model = model
        self._layout = QGridLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(QLabel(model.label + ' :' if model.label else ''), 0, 0)
        self._layout.addWidget(FormComboBoxQt(model), 0, 1)

        if model.id:
            self.setObjectName(model.id)


class FormComboBoxQt(QComboBox):

    def __init__(self, model: SingleSelectComponent):
        super(FormComboBoxQt, self).__init__()
        self.model = model
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.view().setCursor(QCursor(Qt.PointingHandCursor))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        if model.alignment:
            comp_alignment = map_alignment(model.alignment)

            if comp_alignment is not None:
                self.lineEdit().setAlignment(comp_alignment)

        if model.max_width > 0:
            self.setMaximumWidth(int(model.max_width))

        for idx, op in enumerate(self.model.options):
            icon = QIcon(op.icon_path) if op.icon_path else QIcon()
            self.addItem(icon, op.label, op.value)

            if op.tooltip:
                self.setItemData(idx, op.tooltip, Qt.ToolTipRole)

            if model.value and model.value == op:  # default
                self.setCurrentIndex(idx)
                self.setToolTip(model.value.tooltip)

        self.currentIndexChanged.connect(self._set_selected)

        if model.id:
            self.setObjectName(model.id)

    def _set_selected(self, idx: int):
        self.model.value = self.model.options[idx]
        self.setToolTip(self.model.value.tooltip)


class QLineEditObserver(QLineEdit, ViewObserver):

    def __init__(self, **kwargs):
        super(QLineEditObserver, self).__init__(**kwargs)

    def on_change(self, change: str):
        if self.text() != change:
            self.setText(change if change is not None else '')


class QPlainTextEditObserver(QPlainTextEdit, ViewObserver):

    def __init__(self, **kwargs):
        super(QPlainTextEditObserver, self).__init__(**kwargs)

    def on_change(self, change: str):
        self.setText(change)

    def setText(self, text: str):
        if text != self.toPlainText():
            self.setPlainText(text if text is not None else '')

    def setCursorPosition(self, idx: int):
        self.textCursor().setPosition(idx)


class ColorPickerQt(QWidget, ViewObserver):
    def __init__(self, model: ColorPickerComponent):
        super(ColorPickerQt, self).__init__()
        self.model = model
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        

        self.color_btn = QPushButton()
        self.color_btn.setCursor(Qt.PointingHandCursor)
        self.color_btn.setToolTip(model.tooltip if model.tooltip else "")
        self.color_btn.clicked.connect(self._pick_color)
        
        self.hex_input = QLineEdit()
        self.hex_input.setText(model.value)
        self.hex_input.textChanged.connect(self._hex_changed)
        
        self.layout().addWidget(self.color_btn)
        self.layout().addWidget(self.hex_input)
        
        self._update_btn_color(model.value)

        if model.id:
            self.setObjectName(model.id)

    def _update_btn_color(self, hex_color: str):
        self.color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #ccc; border-radius: 4px; min-width: 24px; min-height: 24px;")

    def _hex_changed(self, text: str):
        if text.startswith('#') and (len(text) == 4 or len(text) == 7 or len(text) == 9):
            self._update_btn_color(text)
            self.model.value = text

    def _pick_color(self):
        from PyQt5.QtGui import QColor
        initial = QColor(self.model.value) if self.model.value else Qt.white
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            hex_val = color.name()
            self.hex_input.setText(hex_val)
            self._update_btn_color(hex_val)
            self.model.value = hex_val

    def on_change(self, change: str):
        if self.hex_input.text() != change:
            self.hex_input.setText(change if change is not None else '')
