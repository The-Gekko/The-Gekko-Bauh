from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QWidget, \
    QLabel, QSizePolicy, QHBoxLayout, QTabWidget, QVBoxLayout, \
    QScrollArea, QFrame, QPushButton
from bauh.api.abstract.view import TabGroupComponent, PanelComponent
from bauh.view.util.translation import I18n
from .inputs import QCustomLineEdit


class PanelQt(QWidget):

    def __init__(self, model: PanelComponent, i18n: I18n, parent: QWidget = None):
        super(PanelQt, self).__init__(parent=parent)
        self.model = model
        self.i18n = i18n

        if model.id:
            self.setObjectName(model.id)

        self.setLayout(QVBoxLayout())
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        if model.components:
            for c in model.components:
                from .builder import to_widget
                self.layout().addWidget(to_widget(c, i18n))


class TabGroupQt(QTabWidget):

    def __init__(self, model: TabGroupComponent, i18n: I18n, parent: QWidget = None):
        super(TabGroupQt, self).__init__(parent=parent)
        self.model = model
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.setTabPosition(QTabWidget.North)

        for c in model.tabs:
            try:
                icon = QIcon(c.icon_path) if c.icon_path else QIcon()
            except Exception:
                import logging; logging.error("Exception occurred", exc_info=True)
                icon = QIcon()

            scroll = QScrollArea()
            scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidgetResizable(True)
            from .builder import to_widget
            scroll.setWidget(to_widget(c.get_content(), i18n))
            self.addTab(scroll, icon, c.label)

        self.tabBar().setCursor(QCursor(Qt.PointingHandCursor))


class QSearchBar(QWidget):

    def __init__(self, search_callback, parent: Optional[QWidget] = None):
        super(QSearchBar, self).__init__(parent=parent)
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.callback = search_callback

        self.inp_search = QCustomLineEdit(focus_in_callback=self._set_focus_in,
                                          focus_out_callback=self._set_focus_out)
        self.inp_search.setObjectName('inp_search')
        self.inp_search.setFrame(False)
        self.inp_search.returnPressed.connect(search_callback)
        search_background_color = self.inp_search.palette().color(self.inp_search.backgroundRole()).name()

        self.search_left_corner = QLabel()
        self.search_left_corner.setObjectName('lb_left_corner')

        self.layout().addWidget(self.search_left_corner)

        self.layout().addWidget(self.inp_search)

        self.search_button = QPushButton()
        self.search_button.setObjectName('search_button')
        self.search_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.search_button.clicked.connect(search_callback)

        self.layout().addWidget(self.search_button)

    def clear(self):
        self.inp_search.clear()

    def text(self) -> str:
        return self.inp_search.text()

    def set_text(self, text: str):
        self.inp_search.setText(text)

    def setFocus(self):
        self.inp_search.setFocus()

    def set_tooltip(self, tip: str):
        self.inp_search.setToolTip(tip)

    def set_button_tooltip(self, tip: str):
        self.search_button.setToolTip(tip)

    def set_placeholder(self, placeholder: str):
        self.inp_search.setPlaceholderText(placeholder)

    def _set_focus_in(self):
        self.search_button.setProperty('focused', 'true')
        self.search_left_corner.setProperty('focused', 'true')

        for c in (self.search_button, self.search_left_corner):
            c.style().unpolish(c)
            c.style().polish(c)

    def _set_focus_out(self):
        self.search_button.setProperty('focused', 'false')
        self.search_left_corner.setProperty('focused', 'false')

        for c in (self.search_button, self.search_left_corner):
            c.style().unpolish(c)
            c.style().polish(c)


class QCustomToolbar(QWidget):

    def __init__(self, spacing: int = 2, parent: Optional[QWidget] = None, alignment: Qt.Alignment = Qt.AlignRight,
                 policy_width: QSizePolicy.Policy = QSizePolicy.Minimum,
                 policy_height: QSizePolicy.Policy = QSizePolicy.Preferred):
        super(QCustomToolbar, self).__init__(parent=parent)
        self.setProperty('container', 'true')
        self.setSizePolicy(policy_width, policy_height)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(spacing)
        self.layout().setAlignment(alignment)

    def add_widget(self, widget: QWidget):
        if widget:
            self.layout().addWidget(widget)

    def add_stretch(self, value: int = 0):
        self.layout().addStretch(value)

    def add_space(self, min_width: int = 0):
        self.layout().addWidget(new_spacer(min_width))


def new_spacer(min_width: Optional[int] = None, min_height: Optional[int] = None, max_width: Optional[int] = None) -> QWidget:
    spacer = QWidget()
    spacer.setProperty('spacer', 'true')

    if min_width is not None and min_width >= 0:
        spacer.setMinimumWidth(int(min_width))

    if max_width is not None and max_width >= 0:
        spacer.setMaximumWidth(max_width)

    if min_height is not None and min_height >= 0:
        spacer.setMaximumHeight(int(min_height))

    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return spacer

