import os
import sys
from logging import Logger
from typing import Dict, Optional, Sequence, Tuple

from PyQt5.QtCore import QCoreApplication, QFileSystemWatcher, QObject, QTimer
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

from bauh import __app_name__, __version__
from bauh.stylesheet import contrast_color, dynamic_color_sources, dynamic_theme_kind, is_dark_color, \
    parse_gtk_matugen_colors, process_theme, read_default_themes, read_theme_metada, read_theme_vars, read_user_themes
from bauh.view.util import util, translation
from bauh.view.util.translation import I18n

DEFAULT_I18N_KEY = 'en'
PROPERTY_HARDCODED_STYLESHEET = 'hcqss'

# vigilante activo (uno como mucho por proceso)
_THEME_WATCHER: Optional['ThemeWatcher'] = None
# el proceso de la bandeja lo desactiva: no necesita recargar la hoja de estilo completa
_THEME_WATCHER_ENABLED = True


class ThemeWatcher(QObject):

    """Vigila los ficheros de color de Matugen/GTK y recarga el tema activo cuando cambian."""

    # los editores reemplazan los ficheros de forma atómica y generan varios eventos seguidos
    DEBOUNCE_MS = 300

    def __init__(self, kind: str, app: QCoreApplication, logger: Logger, paths: Sequence[str]):
        super().__init__(app)
        self._kind = kind
        self._app = app
        self._logger = logger
        self._paths = tuple(paths)
        self._reload_pending = False
        self._stopped = False
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_path_changed)
        self._watcher.directoryChanged.connect(self._on_path_changed)
        self.refresh_paths()

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def paths(self) -> Tuple[str, ...]:
        return self._paths

    def refresh_paths(self):
        """Registra los ficheros vigilados y sus directorios padre (Qt deja de vigilar tras un renombrado)."""
        if self._stopped:
            return

        watched_files = set(self._watcher.files())
        watched_dirs = set(self._watcher.directories())

        for path in self._paths:
            parent_dir = os.path.dirname(path)

            if parent_dir and parent_dir not in watched_dirs and os.path.isdir(parent_dir):
                self._watcher.addPath(parent_dir)
                watched_dirs.add(parent_dir)

            if path not in watched_files and os.path.isfile(path):
                self._watcher.addPath(path)
                watched_files.add(path)

    def _on_path_changed(self, path: str):
        if self._stopped:
            return

        # tras un reemplazo atómico la ruta desaparece del vigilante: hay que volver a añadirla
        self.refresh_paths()

        if self._reload_pending:
            return

        self._reload_pending = True
        self._logger.debug(f"theme watcher: change detected at '{path}'")
        QTimer.singleShot(self.DEBOUNCE_MS, self._reload)

    def _reload(self):
        self._reload_pending = False

        if self._stopped:
            return

        self.refresh_paths()

        app_config = read_shared_config(self._logger)
        theme_key = (app_config.get('ui') or {}).get('theme') if app_config else None

        if not theme_key:
            self._logger.warning("theme watcher: no theme defined in the current configuration")
            return

        self._logger.info(f"theme watcher: reloading the '{theme_key}' theme")
        set_theme(theme_key=theme_key, app=self._app, logger=self._logger, app_config=app_config)

    def stop(self):
        """Desconecta el vigilante y libera las rutas registradas."""
        if self._stopped:
            return

        self._stopped = True
        self._watcher.blockSignals(True)

        for paths in (self._watcher.files(), self._watcher.directories()):
            if paths:
                self._watcher.removePaths(paths)

        self.deleteLater()


def read_shared_config(logger: Logger) -> dict:
    """Relee la configuración compartida: nunca se depende de un dict capturado al arrancar."""
    try:
        from bauh.view.core.config import CoreConfigManager
        return CoreConfigManager().get_config()
    except Exception:
        logger.warning("theme watcher: the current configuration could not be read", exc_info=True)
        return {}


def disable_theme_watcher():
    """Desactiva el vigilante de temas (lo usa el proceso de la bandeja)."""
    global _THEME_WATCHER, _THEME_WATCHER_ENABLED
    _THEME_WATCHER_ENABLED = False

    if _THEME_WATCHER is not None:
        _THEME_WATCHER.stop()
        _THEME_WATCHER = None


def update_theme_watcher(theme_key: str, app: QCoreApplication, logger: Logger,
                         available_themes: Optional[Dict[str, str]] = None) -> Optional[ThemeWatcher]:
    """Crea, mantiene o destruye el vigilante según el tema activo sea dinámico o no."""
    global _THEME_WATCHER

    kind = dynamic_theme_kind(theme_key, available_themes) if _THEME_WATCHER_ENABLED else None

    if not kind:
        if _THEME_WATCHER is not None:
            logger.info("theme watcher: stopped (the current theme is not dynamic)")
            _THEME_WATCHER.stop()
            _THEME_WATCHER = None

        return None

    if _THEME_WATCHER is not None:
        if _THEME_WATCHER.kind == kind:
            _THEME_WATCHER.refresh_paths()
            return _THEME_WATCHER

        _THEME_WATCHER.stop()

    _THEME_WATCHER = ThemeWatcher(kind=kind, app=app, logger=logger, paths=dynamic_color_sources(kind))
    logger.info(f"theme watcher: watching the '{kind}' color files")
    return _THEME_WATCHER


def new_qt_application(app_config: dict, logger: Logger, quit_on_last_closed: bool = False, name: str = None) -> QApplication:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(quit_on_last_closed)  # otherwise windows opened through the tray icon kill the application when closed
    app.setApplicationName(name if name else __app_name__)
    app.setApplicationVersion(__version__)

    # Enlaza la ventana con su lanzador .desktop. Sin esto los compositores que agrupan
    # por WM_CLASS (GNOME, Plasma, Hyprland, Niri) muestran la ventana como aplicación
    # desconocida, sin icono ni nombre, y las reglas por clase del usuario no funcionan.
    app.setDesktopFileName(__app_name__)
    app.setWindowIcon(util.get_default_icon()[1])

    if app_config['ui']['qt_style']:
        app.setStyle(str(app_config['ui']['qt_style']))
    else:
        app.setStyle('fusion')

    app.setProperty('qt_style', app.style().objectName().lower())

    theme_key = app_config['ui']['theme'].strip() if app_config['ui']['theme'] else None
    set_theme(theme_key=theme_key, app=app, logger=logger, app_config=app_config)

    return app


def _gen_i18n_data(app_config: dict, locale_dir: str) -> Tuple[str, dict, str, dict]:
    i18n_key, current_i18n = translation.get_locale_keys(app_config['locale'], locale_dir=locale_dir)
    default_i18n = translation.get_locale_keys(DEFAULT_I18N_KEY, locale_dir=locale_dir)[1] if i18n_key != DEFAULT_I18N_KEY else {}
    return i18n_key, current_i18n, DEFAULT_I18N_KEY, default_i18n


def generate_i18n(app_config: dict, locale_dir: str) -> I18n:
    return I18n(*_gen_i18n_data(app_config, locale_dir))


def update_i18n(app_config, locale_dir: str, i18n: I18n) -> I18n:
    cur_key, cur_dict, def_key, def_dict = _gen_i18n_data(app_config, locale_dir)

    if i18n.current_key == cur_key:
        i18n.current.update(cur_dict)

    i18n.default.update(def_dict)
    return i18n


def apply_theme_palette(app: QCoreApplication, theme_vars: Dict[str, str]):
    """Deriva la paleta Qt del tema resuelto para los widgets que el QSS no cubre (diálogos nativos, tooltips...)."""
    background = theme_vars.get('outer_widget.background.color')

    if not is_dark_color(background):
        # los temas claros conservan la paleta estándar del estilo activo
        app.setPalette(app.style().standardPalette())
        return

    base = theme_vars.get('inner_widget.background.color') or background
    text = theme_vars.get('font.color') or contrast_color(background)
    bright_text = theme_vars.get('font.color.bright') or text
    disabled = theme_vars.get('disabled.color') or text
    highlight = theme_vars.get('color.primary') or text
    button = theme_vars.get('pushbutton.background.color') or background

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(background))
    palette.setColor(QPalette.WindowText, QColor(text))
    palette.setColor(QPalette.Base, QColor(base))
    palette.setColor(QPalette.AlternateBase, QColor(background))
    palette.setColor(QPalette.ToolTipBase, QColor(background))
    palette.setColor(QPalette.ToolTipText, QColor(text))
    palette.setColor(QPalette.Text, QColor(text))
    palette.setColor(QPalette.Button, QColor(button))
    palette.setColor(QPalette.ButtonText, QColor(text))
    palette.setColor(QPalette.BrightText, QColor(bright_text))
    palette.setColor(QPalette.Link, QColor(highlight))
    palette.setColor(QPalette.Highlight, QColor(highlight))
    palette.setColor(QPalette.HighlightedText, QColor(contrast_color(highlight)))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(disabled))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(disabled))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(disabled))
    app.setPalette(palette)


def set_theme(theme_key: str, app: QCoreApplication, logger: Logger, app_config: dict = None):
    if not theme_key:
        logger.warning("config: no theme defined")
        return

    available_themes = {}
    default_themes = read_default_themes()
    available_themes.update(default_themes)

    theme_file = None

    if '/' in theme_key:
        if os.path.isfile(theme_key):
            user_sheets = read_user_themes()

            if user_sheets:
                available_themes.update(user_sheets)

                if theme_key in user_sheets:
                    theme_file = theme_key
    else:
        theme_file = default_themes.get(theme_key)

    if not theme_file:
        logger.warning(f"theme '{theme_key}' not found")
        return

    with open(theme_file) as f:
        theme_str = f.read()

    if not theme_str:
        logger.warning("theme file '{}' has no content".format(theme_file))
        return

    base_metadata = read_theme_metada(key=theme_key, file_path=theme_file)

    if base_metadata.abstract:
        logger.warning("theme file '{}' is abstract (abstract = true) and cannot be loaded".format(theme_file))
        return

    # los colores del sistema se leen una sola vez por llamada y se reparten por la cadena de herencia
    kind = dynamic_theme_kind(theme_key, available_themes)
    dynamic_colors = parse_gtk_matugen_colors(kind=kind, logger=logger) if kind else None

    processed = process_theme(file_path=theme_file,
                              metadata=base_metadata,
                              theme_str=theme_str,
                              available_themes=available_themes,
                              app_config=app_config,
                              dynamic_colors=dynamic_colors,
                              logger=logger)

    if not processed:
        logger.warning("theme file '{}' could not be interpreted and processed".format(theme_file))
        return

    app.setStyleSheet(processed[0])
    logger.info("theme file '{}' loaded".format(theme_file))

    if app_config and not app_config.get('ui', {}).get('system_theme'):
        apply_theme_palette(app, read_theme_vars(theme_key, available_themes, dynamic_colors))

    update_theme_watcher(theme_key=theme_key, app=app, logger=logger, available_themes=available_themes)
