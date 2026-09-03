from PyQt5.QtWidgets import QWidget, QLabel

from bauh.api.abstract.view import ViewComponent, SingleSelectComponent, MultipleSelectComponent, TextInputComponent, \
    RangeInputComponent, FormComponent, TabGroupComponent, PanelComponent, TwoStateButtonComponent, TextComponent, \
    SelectViewType, SpacerComponent
from bauh.view.util.translation import I18n

from .inputs import TextInputQt, RangeInputQt, FormQt, ComboSelectQt
from .selects import MultipleSelectQt, RadioSelectQt
from .layout import TabGroupQt, PanelQt, new_spacer
from .buttons import TwoStateButtonQt


def new_single_select(model: SingleSelectComponent) -> QWidget:
    if model.type == SelectViewType.RADIO:
        return RadioSelectQt(model)
    elif model.type == SelectViewType.COMBO:
        return ComboSelectQt(model)
    else:
        raise Exception("Unsupported type {}".format(model.type))


def to_widget(comp: ViewComponent, i18n: I18n, parent: QWidget = None) -> QWidget:
    if isinstance(comp, SingleSelectComponent):
        return new_single_select(comp)
    elif isinstance(comp, MultipleSelectComponent):
        return MultipleSelectQt(comp, None)
    elif isinstance(comp, TextInputComponent):
        return TextInputQt(comp)
    elif isinstance(comp, RangeInputComponent):
        return RangeInputQt(comp)
    elif isinstance(comp, FormComponent):
        return FormQt(comp, i18n)
    elif isinstance(comp, TabGroupComponent):
        return TabGroupQt(comp, i18n, parent)
    elif isinstance(comp, PanelComponent):
        return PanelQt(comp, i18n, parent)
    elif isinstance(comp, TwoStateButtonComponent):
        return TwoStateButtonQt(comp)
    elif isinstance(comp, SpacerComponent):
        # los espaciadores no tienen estado propio: se delega en la fabrica de layout.py
        return new_spacer()
    elif isinstance(comp, TextComponent):
        label = QLabel(comp.value)

        if comp.min_width is not None and comp.min_width > 0:
            label.setMinimumWidth(comp.min_width)

        if comp.max_width is not None and comp.max_width > 0:
            label.setMaximumWidth(comp.max_width)

        if comp.tooltip:
            label.setToolTip(comp.tooltip)

        label.setProperty('has_action', 'false')
        if comp.size == 12:
            label.setProperty('h1', 'true')
        elif comp.size == 11:
            label.setProperty('h2', 'true')
        elif comp.size == 10:
            label.setProperty('h3', 'true')

        if hasattr(comp, 'html') and comp.html or (isinstance(comp.value, str) and '<' in comp.value and '>' in comp.value):
            label.setTextFormat(1)
            label.setOpenExternalLinks(True)

        return label

    raise Exception("Unknown component: {}".format(comp.__class__.__name__))
