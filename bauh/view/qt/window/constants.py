"""Constantes compartidas por la ventana principal y sus mixins."""

# nombre visible de la aplicacion (marca del fork)
DISPLAY_NAME = 'bauh Gekko Edition'

DARK_ORANGE = '#FF4500'

# identificadores de accion
ACTION_APPLY_FILTERS = 1
ACTION_SEARCH = 2
ACTION_INSTALL = 3
ACTION_UNINSTALL = 4
ACTION_INFO = 5
ACTION_HISTORY = 6
ACTION_DOWNGRADE = 7
ACTION_UPGRADE = 8
ACTION_LAUNCH = 9
ACTION_CUSTOM_ACTION = 10
ACTION_SCREENSHOTS = 11
ACTION_IGNORE_UPDATES = 12

# identificadores de componente
SEARCH_BAR = 1
BT_INSTALLED = 2
BT_REFRESH = 3
BT_SUGGESTIONS = 4
BT_UPGRADE = 5
CHECK_INSTALLED = 6
CHECK_UPDATES = 7
CHECK_APPS = 8
COMBO_TYPES = 9
CHECK_VERIFIED = 10
COMBO_CATEGORIES = 11
INP_NAME = 12
CHECK_DETAILS = 13
BT_SETTINGS = 14
BT_CUSTOM_ACTIONS = 15
BT_ABOUT = 16
BT_THEMES = 17
BT_MATUGEN = 18

# identificadores de grupo de componentes
GROUP_FILTERS = 1
GROUP_VIEW_INSTALLED = 2
GROUP_VIEW_SEARCH = 3
GROUP_UPPER_BAR = 4
GROUP_LOWER_BTS = 5

# acciones de la ventana que mantienen un proceso privilegiado en marcha y por
# tanto no deben interrumpirse cerrando la ventana sin confirmacion
BLOCKING_ACTIONS = (ACTION_INSTALL, ACTION_UNINSTALL, ACTION_UPGRADE, ACTION_DOWNGRADE, ACTION_CUSTOM_ACTION)
