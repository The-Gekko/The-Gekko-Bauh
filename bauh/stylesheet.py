import glob
import os
import re
from logging import Logger
from typing import Optional, Dict, Tuple, Set, Iterable, List

from bauh.api.paths import USER_THEMES_DIR
from bauh.view.util import resource
from bauh.view.util.translation import I18n

# RE_WIDTH_PERCENT = re.compile(r'[\d\\.]+%w') TODO percentage measures disabled for the moment (requires more testing)
# RE_HEIGHT_PERCENT = re.compile(r'[\d\\.]+%h') TODO percentage measures disabled for the moment (requires more testing)
RE_META_I18N_FIELDS = re.compile(r'((name|description)(\[\w+])?)')
RE_VAR_PATTERN = re.compile(r'^@[\w.\-_]+')
RE_QSS_EXT = re.compile(r'\.qss$')
# referencias '@variable' que siguen presentes en una hoja ya procesada
RE_UNRESOLVED_VAR = re.compile(r'@[a-zA-Z][\w.\-]*')
# color aceptado por Qt: hexadecimal, rgb()/rgba() o un nombre CSS
RE_CSS_COLOR = re.compile(r'^(?:#[0-9a-fA-F]{3,8}|rgba?\([^()]*\)|[a-zA-Z]{3,20})$')
RE_HEX_COLOR = re.compile(r'^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
RE_DEFINE_COLOR = re.compile(r'@define-color\s+([\w\-]+)\s+([^;]+);')
RE_CSS_IMPORT = re.compile(r'@import\s+(?:url\()?["\']?([^"\')\s]+)["\']?\)?\s*;')
RE_COLOR_FUNCTION = re.compile(r'^(?:alpha|shade|mix|darker|lighter|transparentize)\s*\((.+)\)$', re.IGNORECASE)
RE_RGB_FUNCTION = re.compile(r'^rgba?\(([^()]*)\)$', re.IGNORECASE)

# claves de los temas que derivan sus colores del sistema en tiempo real
DYNAMIC_THEME_KEYS = ('matugen', 'gtk')
# ficheros de color generados por Matugen
MATUGEN_COLOR_FILES = ('~/.cache/matugen/colors-gtk.css',)
# ficheros de color de GTK 3/4 (el sistema primero, el usuario después)
GTK_COLOR_FILES = ('/etc/gtk-3.0/gtk.css', '/etc/gtk-4.0/gtk.css',
                   '~/.config/gtk-3.0/gtk.css', '~/.config/gtk-4.0/gtk.css')
# límites para las resoluciones iterativas (evitan bucles con definiciones cíclicas)
MAX_COLOR_REF_ITERATIONS = 10
MAX_CSS_IMPORT_DEPTH = 3


class ThemeMetadata:

    def __init__(self, file_path: str, default: bool, default_name: Optional[str] = None,
                 default_description: Optional[str] = None, version: Optional[str] = None,
                 root_theme: Optional[str] = None, abstract: bool = False):
        self.names = {}
        self.default_name = default_name
        self.descriptions = {}
        self.default_description = default_description
        self.root_theme = root_theme
        self.version = version
        self.file_path = file_path
        self.file_dir = '/'.join(file_path.split('/')[0:-1])
        self.default = default
        self.key = self.file_path.split('/')[-1].split('.')[0] if self.default else self.file_path
        self.abstract = abstract

    def __eq__(self, other) -> bool:
        if isinstance(other, ThemeMetadata):
            return self.file_path == other.file_path

        return False

    def __hash__(self):
        return self.file_path.__hash__()

    def __repr__(self):
        return self.file_path if self.file_path else ''

    def get_i18n_name(self, i18n: I18n) -> str:
        if self.names:
            name = self.names.get(i18n.current_key, self.names.get(i18n.default_key))

            if name:
                return name

        if self.default_name:
            return self.default_name
        else:
            return self.file_path.split('/')[-1]

    def get_i18n_description(self, i18n: I18n) -> Optional[str]:
        if self.descriptions:
            des = self.descriptions.get(i18n.current_key, self.descriptions.get(i18n.default_key))

            if des:
                return des

        return self.default_description


def read_theme_metada(key: str, file_path: str) -> ThemeMetadata:
    meta_file = RE_QSS_EXT.sub('.meta', file_path)
    meta_obj = ThemeMetadata(file_path=file_path, default_name=key, default=not key.startswith('/'))

    if os.path.exists(meta_file):
        meta_dict = {}
        with open(meta_file) as f:
            for line in f.readlines():
                if line:
                    # split acotado: preserva los valores que contienen '='
                    field_split = line.split('=', 1)

                    if len(field_split) > 1:
                        meta_dict[field_split[0].strip()] = field_split[1].strip()

            if meta_dict:
                for field, val in meta_dict.items():
                    if field == 'version':
                        meta_obj.version = val
                    elif field == 'root_theme':
                        meta_obj.root_theme = val
                    elif field == 'name':
                        meta_obj.default_name = val
                    elif field == 'description':
                        meta_obj.default_description = val
                    elif field == 'abstract':
                        boolean = val.lower()

                        if boolean == 'true':
                            meta_obj.abstract = True
                        elif boolean == 'false':
                            meta_obj.abstract = False

                    else:
                        i18n_field = RE_META_I18N_FIELDS.findall(field)

                        if i18n_field:
                            if i18n_field[0][1] == 'name':
                                meta_obj.names[i18n_field[0][2][1:-1]] = val
                            else:
                                meta_obj.descriptions[i18n_field[0][2][1:-1]] = val

    return meta_obj


def read_default_themes() -> Dict[str, str]:
    """Descubre por glob los temas incluidos con la aplicación (uno por fichero .qss)."""
    return {f.split('/')[-1].split('.')[0].lower(): f for f in glob.glob(resource.get_path('style/**/*.qss'))}


def read_user_themes() -> Dict[str, str]:
    return {f: f for f in glob.glob('{}/**/*.qss'.format(USER_THEMES_DIR), recursive=True)}


def read_all_themes_metadata() -> Set[ThemeMetadata]:
    themes = set()

    for key, file_path in read_default_themes().items():
        themes.add(read_theme_metada(key=key, file_path=file_path))

    for key, file_path in read_user_themes().items():
        themes.add(read_theme_metada(key=key, file_path=file_path))

    return themes


def read_theme_chain(theme_key: str, available_themes: Optional[Dict[str, str]] = None) -> Tuple[str, ...]:
    """Devuelve la cadena de herencia de un tema, de la hoja hacia la raíz."""
    if not theme_key:
        return ()

    if available_themes is None:
        available_themes = read_default_themes()

    chain, visited, current = [], set(), theme_key

    while current and current not in visited:
        visited.add(current)
        chain.append(current)

        file_path = available_themes.get(current)

        if not file_path or not os.path.isfile(file_path):
            break

        current = read_theme_metada(key=current, file_path=file_path).root_theme

    return tuple(chain)


def dynamic_theme_kind(theme_key: str, available_themes: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Indica si un tema (o alguno de sus ancestros) es dinámico: 'matugen', 'gtk' o None."""
    for key in read_theme_chain(theme_key, available_themes):
        normalized = key.strip().lower()

        if normalized in DYNAMIC_THEME_KEYS:
            return normalized

    return None


def dynamic_color_sources(kind: Optional[str]) -> Tuple[str, ...]:
    """Ficheros de color a leer según el tipo de tema dinámico (sistema primero, usuario después)."""
    if kind == 'matugen':
        sources = MATUGEN_COLOR_FILES
    elif kind == 'gtk':
        sources = GTK_COLOR_FILES
    else:
        sources = (*GTK_COLOR_FILES, *MATUGEN_COLOR_FILES)

    return tuple(os.path.expanduser(path) for path in sources)


def parse_gtk_matugen_colors(kind: Optional[str] = None, logger: Optional[Logger] = None,
                             sources: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Lee las declaraciones '@define-color' de Matugen/GTK y las normaliza a colores usables por Qt."""
    files = tuple(sources) if sources is not None else dynamic_color_sources(kind)

    raw: Dict[str, str] = {}

    for file_path in files:
        expanded = os.path.expanduser(file_path)

        if os.path.isfile(expanded):
            raw.update(_read_define_colors(expanded, logger=logger))

    colors = _resolve_color_references(raw, logger=logger)

    if logger:
        logger.info(f"dynamic theme ({kind or 'auto'}): {len(colors)} color(s) read "
                    f"from {len(files)} candidate file(s)")

    return colors


def _read_define_colors(file_path: str, logger: Optional[Logger] = None,
                        visited: Optional[Set[str]] = None, depth: int = 0) -> Dict[str, str]:
    """Lee un CSS de GTK devolviendo sus '@define-color' y siguiendo los '@import' relativos."""
    if visited is None:
        visited = set()

    real_path = os.path.realpath(os.path.expanduser(file_path))

    if depth > MAX_CSS_IMPORT_DEPTH or real_path in visited:
        return {}

    visited.add(real_path)

    try:
        with open(real_path, encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        if logger:
            logger.warning(f"could not read the GTK color file '{real_path}': {e}")

        return {}

    colors: Dict[str, str] = {}
    base_dir = os.path.dirname(real_path)

    # los '@import' se procesan primero: el fichero que los declara tiene prioridad
    for import_path in RE_CSS_IMPORT.findall(content):
        resolved = _resolve_css_import(import_path, base_dir)

        if resolved:
            colors.update(_read_define_colors(resolved, logger=logger, visited=visited, depth=depth + 1))
        elif logger:
            logger.warning(f"could not resolve the '@import' of '{import_path}' declared in '{real_path}'")

    for match in RE_DEFINE_COLOR.finditer(content):
        colors[match.group(1)] = match.group(2).strip()

    return colors


def _resolve_css_import(import_path: str, base_dir: str) -> Optional[str]:
    """Resuelve la ruta de un '@import' respecto al directorio del fichero que lo declara."""
    candidate = os.path.expanduser(import_path.replace('file://', '').strip())

    if not os.path.isabs(candidate):
        candidate = os.path.join(base_dir, candidate)

    return candidate if os.path.isfile(candidate) else None


def _split_css_args(expression: str) -> List[str]:
    """Divide los argumentos de una función CSS por las comas de primer nivel."""
    args, depth, current = [], 0, []

    for char in expression:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1

        if char == ',' and depth == 0:
            args.append(''.join(current))
            current = []
        else:
            current.append(char)

    args.append(''.join(current))
    return args


def _unwrap_color_function(value: str) -> str:
    """Reduce funciones de GTK (alpha, mix, shade...) a su primer argumento de color."""
    current = value.strip()

    for _ in range(MAX_COLOR_REF_ITERATIONS):
        match = RE_COLOR_FUNCTION.match(current)

        if not match:
            break

        current = _split_css_args(match.group(1))[0].strip()

    return current


def _resolve_color_references(raw: Dict[str, str], logger: Optional[Logger] = None) -> Dict[str, str]:
    """Resuelve las referencias '@otro_color' de forma iterativa y acotada, descartando lo inválido."""
    values = {key: _unwrap_color_function(val) for key, val in raw.items()}

    for _ in range(MAX_COLOR_REF_ITERATIONS):
        changed = False

        for key, value in values.items():
            if value.startswith('@'):
                target = values.get(value[1:])

                if target is not None and target != value:
                    values[key] = _unwrap_color_function(target)
                    changed = True

        if not changed:
            break

    final = {}

    for key, value in values.items():
        if RE_CSS_COLOR.match(value):
            final[key] = value
        elif logger:
            logger.warning(f"ignoring the GTK color '{key}': unsupported value '{value}'")

    return final


# Nombres CSS que aparecen de verdad en los temas de GTK y en las plantillas de Matugen. Se
# usan como respaldo cuando PyQt5 no está disponible (la suite sin Qt de la integración continua).
CSS_COLOR_NAMES = {'black': '#000000', 'white': '#FFFFFF', 'red': '#FF0000', 'green': '#008000',
                   'blue': '#0000FF', 'gray': '#808080', 'grey': '#808080', 'silver': '#C0C0C0',
                   'transparent': '#000000', 'orange': '#FFA500', 'yellow': '#FFFF00',
                   'purple': '#800080', 'navy': '#000080', 'teal': '#008080', 'lime': '#00FF00',
                   'maroon': '#800000', 'olive': '#808000', 'aqua': '#00FFFF', 'cyan': '#00FFFF',
                   'fuchsia': '#FF00FF', 'magenta': '#FF00FF'}


def _color_name_to_hex(name: str) -> Optional[str]:
    """Traduce un nombre de color CSS a '#RRGGBB'."""
    try:
        from PyQt5.QtGui import QColor

        color = QColor(name)

        if color.isValid():
            return f'#{color.red():02X}{color.green():02X}{color.blue():02X}'
    except ImportError:
        pass

    return CSS_COLOR_NAMES.get(name)


def _parse_rgb_function(color: str) -> Optional[Tuple[int, int, int]]:
    """Convierte 'rgb(r, g, b)' o 'rgba(r, g, b, a)' en una tupla RGB. Acepta porcentajes."""
    match = RE_RGB_FUNCTION.match(color.strip())

    if not match:
        return None

    args = [arg.strip() for arg in _split_css_args(match.group(1))]

    if len(args) not in (3, 4):
        return None

    channels = []

    for arg in args[:3]:
        try:
            value = float(arg[:-1]) * 255 / 100 if arg.endswith('%') else float(arg)
        except ValueError:
            return None

        channels.append(max(0, min(255, int(round(value)))))

    return channels[0], channels[1], channels[2]


def normalize_color(color: Optional[str]) -> Optional[str]:
    """Devuelve el color como '#RRGGBB', o None si no se puede interpretar.

    Los ficheros de GTK y de Matugen declaran colores como 'rgb(30, 30, 46)' o con nombres CSS
    ('white'), formatos que Qt entiende en una hoja de estilo pero que el resto de utilidades de
    este módulo (luminancia, mezcla, contraste) no sabían leer: devolvían None y la paleta
    derivada acababa pintando texto negro sobre fondo oscuro.
    """
    if not color:
        return None

    value = color.strip()

    if RE_HEX_COLOR.match(value):
        digits = value[1:]

        if len(digits) in (3, 4):
            digits = ''.join(char * 2 for char in digits)

        return f'#{digits[:6].upper()}'

    rgb = _parse_rgb_function(value)

    if rgb is not None:
        return '#{:02X}{:02X}{:02X}'.format(*rgb)

    return _color_name_to_hex(value.lower())


def _parse_hex_color(color: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """Convierte un color en una tupla RGB (ignora el canal alfa)."""
    normalized = normalize_color(color)

    if not normalized:
        return None

    color = normalized

    if not color or not RE_HEX_COLOR.match(color.strip()):
        return None

    digits = color.strip()[1:]

    if len(digits) in (3, 4):
        digits = ''.join(char * 2 for char in digits)

    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def color_luminance(color: Optional[str]) -> Optional[float]:
    """Luminancia relativa (0-1) de un color hexadecimal, o None si no se puede interpretar."""
    rgb = _parse_hex_color(color)

    if rgb is None:
        return None

    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255


def is_dark_color(color: Optional[str]) -> bool:
    """Indica si un color hexadecimal es oscuro (los no interpretables se consideran claros)."""
    luminance = color_luminance(color)
    return luminance is not None and luminance < 0.45


def contrast_color(color: Optional[str]) -> str:
    """Devuelve blanco o negro según lo que contraste mejor con el color indicado."""
    return '#FFFFFF' if is_dark_color(color) else '#000000'


def blend_colors(color: Optional[str], other: Optional[str], ratio: float) -> Optional[str]:
    """Mezcla dos colores hexadecimales dando a 'color' el peso 'ratio' (0-1)."""
    first, second = _parse_hex_color(color), _parse_hex_color(other)

    if first is None or second is None:
        return color

    mixed = tuple(round(first[i] * ratio + second[i] * (1 - ratio)) for i in range(3))
    return '#{:02X}{:02X}{:02X}'.format(*mixed)


def read_fallback_colors() -> Dict[str, str]:
    """Variables de aurora.vars usadas como respaldo cuando falta un color del sistema."""
    aurora_file = read_default_themes().get('aurora')

    if aurora_file and os.path.isfile(aurora_file):
        return _read_var_file(aurora_file)

    return {}


def build_dynamic_var_overrides(colors: Dict[str, str],
                                fallbacks: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Traduce los colores de Matugen/GTK a las variables crudas del tema Aurora."""
    base = read_fallback_colors() if fallbacks is None else fallbacks

    def pick(*names: str, fallback_var: str, default: str) -> str:
        for name in names:
            value = colors.get(name)

            if value:
                return value

        return base.get(fallback_var) or default

    bg = pick('window_bg_color', 'theme_bg_color',
              fallback_var='outer_widget.background.color', default='#161B22')
    view_bg = pick('view_bg_color', 'theme_base_color',
                   fallback_var='inner_widget.background.color', default='#0D1117')
    fg = pick('window_fg_color', 'theme_fg_color', fallback_var='font.color', default='#C9D1D9')
    sidebar_bg = pick('sidebar_bg_color', 'headerbar_bg_color',
                      fallback_var='color.surface.medium', default='#21262D')
    accent = pick('accent_color', 'accent_bg_color', 'theme_selected_bg_color',
                  fallback_var='color.primary', default='#58A6FF')
    card_bg = pick('card_bg_color', 'popover_bg_color', fallback_var='color.surface.light', default='#30363D')
    destructive = pick('destructive_color', 'error_color', fallback_var='color.error', default='#FF7B72')
    warning = pick('warning_color', fallback_var='color.warning', default='#E3B341')
    success = pick('success_color', fallback_var='color.accent', default='#7EE787')
    accent_fg = colors.get('accent_fg_color') or contrast_color(accent)

    # variables derivadas: sin ellas se quedarían con los valores de Aurora sobre una paleta ajena
    muted = blend_colors(fg, bg, 0.65)
    disabled = blend_colors(fg, bg, 0.45)
    hover = blend_colors(card_bg, fg, 0.9)
    # el boton primario se aclara al pasar el raton y se oscurece al pulsarlo, igual que hace
    # Aurora con su verde, pero partiendo del acento del sistema
    ok_hover = blend_colors(accent, fg, 0.85)
    ok_pressed = blend_colors(accent, bg, 0.75)

    return {
        'color.primary': accent,
        'color.primary.dim': accent,
        'color.primary.bright': accent,
        'color.secondary': accent,
        'color.secondary.dim': accent,
        'color.accent': success,
        'color.accent.dim': success,
        'color.cyan': accent,
        'color.cyan.dim': accent,
        'color.success': success,
        'color.info': accent,
        'color.warning': warning,
        'color.yellow_dark': warning,
        'color.error': destructive,
        'color.surface.darkest': view_bg,
        'color.surface.dark': bg,
        'color.surface.medium': sidebar_bg,
        'color.surface.light': card_bg,
        'color.surface.lighter': card_bg,
        'color.surface.hover': hover,
        'font.color': fg,
        'font.color.bright': fg,
        'font.color.muted': muted,
        'disabled.color': disabled,
        'outer_widget.background.color': bg,
        'inner_widget.background.color': view_bg,
        'pushbutton.background.color': sidebar_bg,
        'lineedit.background.color': view_bg,
        'focus.border.color': accent,
        'tab.font.color': accent,
        'tab.underline.color': accent,
        'progressbar.fill.color': accent,
        'console.background.color': view_bg,
        'console.font.color': fg,
        'button_ok.background.color': accent,
        'button_ok.font.color': accent_fg,
        # sin estas dos, el boton primario saltaba al verde fijo de Aurora al pasar el raton,
        # rompiendo justo la sincronizacion con el sistema que estos temas persiguen
        'button_ok.hover.background.color': ok_hover,
        'button_ok.pressed.background.color': ok_pressed,
        'menu.item.selected.background.color': accent,
        'menu.item.selected.font.color': accent_fg,
        'table.selection.background.color': card_bg,
        'history.version.focus.color': fg
    }


def read_theme_vars(theme_key: str, available_themes: Optional[Dict[str, str]] = None,
                    dynamic_colors: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Variables efectivas de un tema, resolviendo su cadena de herencia desde la raíz."""
    if available_themes is None:
        available_themes = read_default_themes()

    overrides = build_dynamic_var_overrides(dynamic_colors) if dynamic_colors else None
    merged: Dict[str, str] = {}

    for key in reversed(read_theme_chain(theme_key, available_themes)):
        file_path = available_themes.get(key)

        if file_path and os.path.isfile(file_path):
            merged.update(_read_var_file(file_path, overrides=overrides))

    return merged


def process_theme(file_path: str, theme_str: str, metadata: ThemeMetadata,
                  available_themes: Optional[Dict[str, str]], app_config: dict = None,
                  dynamic_colors: Optional[Dict[str, str]] = None,
                  logger: Optional[Logger] = None) -> Optional[Tuple[str, ThemeMetadata]]:
    if theme_str and metadata:
        root_theme = None

        if metadata.root_theme and available_themes and metadata.root_theme in available_themes:
            root_file = available_themes[metadata.root_theme]

            if os.path.isfile(root_file):
                with open(root_file) as f:
                    root_theme_str = f.read()

                if root_theme_str:
                    root_metadata = read_theme_metada(key=metadata.root_theme, file_path=root_file)
                    # el tema personalizado solo se añade en el nivel externo (evita repetirlo por herencia)
                    root_theme = process_theme(file_path=root_file,
                                               theme_str=root_theme_str,
                                               metadata=root_metadata,
                                               available_themes=available_themes,
                                               app_config=None,
                                               dynamic_colors=dynamic_colors,
                                               logger=logger)

        # los colores dinámicos se aplican sobre las variables crudas: así también cambian las derivadas
        overrides = build_dynamic_var_overrides(dynamic_colors) if dynamic_colors else None
        var_map = _read_var_file(file_path, overrides=overrides)
        var_map['images'] = resource.get_path('img')
        var_map['style_dir'] = metadata.file_dir

        if var_map:
            var_list = [*var_map.keys()]
            var_list.sort(key=_by_str_len, reverse=True)

            for var in var_list:
                theme_str = theme_str.replace('@' + var, var_map[var])

        _warn_unresolved_vars(theme_str, file_path, logger)

        if app_config:
            theme_str += gen_custom_theme_css(app_config, logger=logger)

        return theme_str if not root_theme else '{}\n{}'.format(root_theme[0], theme_str), metadata


def _warn_unresolved_vars(theme_str: str, file_path: str, logger: Optional[Logger] = None):
    """Avisa de las referencias '@variable' que no se han podido sustituir."""
    if not logger:
        return

    unresolved = sorted({match for match in RE_UNRESOLVED_VAR.findall(theme_str)})

    if unresolved:
        logger.warning(f"theme file '{file_path}' has {len(unresolved)} unresolved variable(s): "
                       f"{', '.join(unresolved[0:10])}")


def valid_color(value: Optional[str], field: str = 'color', logger: Optional[Logger] = None) -> Optional[str]:
    """Devuelve el color solo si Qt puede interpretarlo; en caso contrario avisa y lo descarta."""
    if not value:
        return None

    candidate = str(value).strip()

    if RE_CSS_COLOR.match(candidate):
        return candidate

    if logger:
        logger.warning(f"custom theme: ignoring the invalid '{field}' value '{value}'")

    return None


def _quote_css_url(path: str) -> str:
    """Escapa una ruta para poder incrustarla entre comillas dentro de un url() de QSS."""
    return path.replace('\\', '\\\\').replace('"', '\\"')


def gen_custom_theme_css(app_config: dict, logger: Optional[Logger] = None) -> str:
    """Genera el QSS del tema personalizado del usuario validando colores y rutas."""
    custom_theme = app_config.get('custom_theme') or {}

    if not custom_theme.get('enabled', False):
        return ''

    bg_color = valid_color(custom_theme.get('background_color'), 'background_color', logger)
    text_color = valid_color(custom_theme.get('text_color'), 'text_color', logger)
    accent_color = valid_color(custom_theme.get('accent_color'), 'accent_color', logger)
    bg_image = custom_theme.get('background_image')

    custom_css = "\n/* Custom Theme Overrides */\n"

    if bg_color or text_color:
        custom_css += "QWidget { "
        if bg_color:
            custom_css += f"background-color: {bg_color}; "
        if text_color:
            custom_css += f"color: {text_color}; "
        custom_css += "}\n"

        custom_css += "QMenuBar, QMenu { "
        if bg_color:
            custom_css += f"background-color: {bg_color}; "
        if text_color:
            custom_css += f"color: {text_color}; "
        custom_css += "}\n"

        custom_css += (f"QToolTip {{ background-color: {bg_color or '#000'}; color: {text_color or '#fff'}; "
                       f"border: 1px solid {accent_color or '#555'}; }}\n")

    if bg_image and os.path.exists(bg_image):
        custom_css += (f'QWidget#manage_window {{ background-image: url("{_quote_css_url(bg_image)}"); '
                       f'background-position: center; background-repeat: no-repeat; }}\n')

    if accent_color:
        custom_css += f"QPushButton:hover {{ border-color: {accent_color}; }}\n"
        custom_css += f"QProgressBar::chunk {{ background-color: {accent_color}; }}\n"
        custom_css += f"QTabBar::tab:selected {{ border-bottom: 2px solid {accent_color}; color: {accent_color}; }}\n"
        custom_css += (f"QCheckBox::indicator:checked {{ background-color: {accent_color}; "
                       f"border-color: {accent_color}; }}\n")
        custom_css += (f"QRadioButton::indicator:checked {{ background-color: {accent_color}; "
                       f"border-color: {accent_color}; }}\n")
        custom_css += f"QSlider::handle:horizontal {{ background-color: {accent_color}; }}\n"

    return custom_css


def _by_str_len(string: str) -> int:
    return len(string)


def _read_var_file(theme_file: str, overrides: Optional[Dict[str, str]] = None) -> dict:
    vars_file = theme_file.replace('.qss', '.vars')
    var_map = {}

    if os.path.isfile(vars_file):
        with open(vars_file) as f:
            for line in f.readlines():
                if line:
                    line_strip = line.strip()
                    if line_strip:
                        # split acotado: preserva los valores que contienen '='
                        var_value = line_strip.split('=', 1)

                        if var_value and len(var_value) == 2:
                            var, value = var_value[0].strip(), var_value[1].strip()

                            if var and value:
                                var_map[var] = value

    if overrides:
        var_map.update(overrides)

    if var_map:
        process_var_of_vars(var_map)  # mapping keys that point to others

    return var_map


def process_var_of_vars(var_map: dict):
    while True:
        pending_vars, invalid = {}, set()

        for k, v in var_map.items():
            var_match = RE_VAR_PATTERN.match(v)

            if var_match:
                var_name = var_match.group()[1:]
                if var_name not in var_map or var_name == k:
                    invalid.add(k)
                else:
                    pending_vars[k] = var_name

        for key in invalid:
            del var_map[key]

        if not pending_vars:
            break

        resolved = 0

        for key, val in pending_vars.items():
            real_val = var_map[val]

            if not RE_VAR_PATTERN.match(real_val):
                var_map[key] = real_val
                resolved += 1

        if resolved == 0:
            # ciclo entre variables: se descartan las pendientes para no bloquear el arranque
            for key in pending_vars:
                del var_map[key]

            break

        if resolved == len(pending_vars):
            break


# TODO percentage measures disabled for the moment (requires more testing)
# def process_width_percent_measures(theme: str, screen_width: int) -> str:
#     width_measures = RE_WIDTH_PERCENT.findall(theme)
#
#     final_theme = theme
#     if width_measures:
#         for m in width_measures:
#             try:
#                 percent = float(m.split('%')[0])
#                 final_theme = final_theme.replace(m, '{}px'.format(round(screen_width * percent)))
#             except ValueError:
#                 import logging; logging.error("Exception occurred", exc_info=True)
#
#     return final_theme


# def process_height_percent_measures(theme: str, screen_height: int) -> str:
#     width_measures = RE_HEIGHT_PERCENT.findall(theme)
#
#     final_sheet = theme
#     if width_measures:
#         for m in width_measures:
#             try:
#                 percent = float(m.split('%')[0])
#                 final_sheet = final_sheet.replace(m, '{}px'.format(round(screen_height * percent)))
#             except ValueError:
#                 import logging; logging.error("Exception occurred", exc_info=True)
#
#     return final_sheet
