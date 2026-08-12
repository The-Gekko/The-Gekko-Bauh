import glob
import os
import re
from typing import Optional, Dict, Tuple, Set

from bauh.api.paths import USER_THEMES_DIR
from bauh.view.util import resource
from bauh.view.util.translation import I18n

# RE_WIDTH_PERCENT = re.compile(r'[\d\\.]+%w') TODO percentage measures disabled for the moment (requires more testing)
# RE_HEIGHT_PERCENT = re.compile(r'[\d\\.]+%h') TODO percentage measures disabled for the moment (requires more testing)
RE_META_I18N_FIELDS = re.compile(r'((name|description)(\[\w+])?)')
RE_VAR_PATTERN = re.compile(r'^@[\w.\-_]+')
RE_QSS_EXT = re.compile(r'\.qss$')


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
                    field_split = line.split('=')

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
    themes = {f.split('/')[-1].split('.')[0].lower(): f for f in glob.glob(resource.get_path('style/**/*.qss'))}
    # Asegurar que los temas dinámicos matugen y gtk estén disponibles
    if 'aurora' in themes:
        themes['matugen'] = themes['aurora']
        themes['gtk'] = themes['aurora']
    return themes


def parse_gtk_matugen_colors() -> dict:
    """Parsea las variables @define-color de Matugen y GTK 3/4 para mapearlas a Bauh."""
    colors = {}
    candidates = [
        os.path.expanduser('~/.cache/matugen/colors-gtk.css'),
        os.path.expanduser('~/.config/gtk-3.0/gtk.css'),
        os.path.expanduser('~/.config/gtk-4.0/gtk.css'),
        '/etc/gtk-3.0/gtk.css'
    ]

    re_define_color = re.compile(r'@define-color\s+([\w\-_]+)\s+(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\));')

    for file_path in candidates:
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Si incluye un @import, intentar seguirlo
                for import_match in re.findall(r'@import\s+(?:url\()?["\']?([^"\'\)\s]+)["\']?\)?;', content):
                    import_path = import_match.replace('file://', '')
                    if os.path.isfile(import_path):
                        with open(import_path, 'r', encoding='utf-8') as imp_f:
                            for match in re_define_color.finditer(imp_f.read()):
                                colors[match.group(1)] = match.group(2)

                for match in re_define_color.finditer(content):
                    colors[match.group(1)] = match.group(2)
            except Exception:
                pass

    return colors


def read_user_themes() -> Dict[str, str]:
    return {f: f for f in glob.glob('{}/**/*.qss'.format(USER_THEMES_DIR), recursive=True)}


def read_all_themes_metadata() -> Set[ThemeMetadata]:
    themes = set()

    for key, file_path in read_default_themes().items():
        themes.add(read_theme_metada(key=key, file_path=file_path))

    for key, file_path in read_user_themes().items():
        themes.add(read_theme_metada(key=key, file_path=file_path))

    return themes


def process_theme(file_path: str, theme_str: str, metadata: ThemeMetadata,
                  available_themes: Optional[Dict[str, str]], app_config: dict = None) -> Optional[Tuple[str, ThemeMetadata]]:
    if theme_str and metadata:
        root_theme = None
        if metadata.root_theme and metadata.root_theme in available_themes:
            root_file = available_themes[metadata.root_theme]

            if os.path.isfile(root_file):
                with open(root_file) as f:
                    root_theme_str = f.read()

                if root_theme_str:
                    root_metadata = read_theme_metada(key=metadata.root_theme, file_path=root_file)
                    root_theme = process_theme(file_path=root_file,
                                               theme_str=root_theme_str,
                                               metadata=root_metadata,
                                               available_themes=available_themes,
                                               app_config=app_config)

        var_map = _read_var_file(file_path)
        var_map['images'] = resource.get_path('img')
        var_map['style_dir'] = metadata.file_dir

        # Matugen / GTK Dynamic Theme Mapping
        current_theme_key = (metadata.key or '').lower()
        cfg_theme = (app_config.get('ui', {}).get('theme') or '').lower() if app_config else ''
        
        if current_theme_key in ('matugen', 'gtk') or cfg_theme in ('matugen', 'gtk'):
            gtk_colors = parse_gtk_matugen_colors()
            if gtk_colors:
                bg = gtk_colors.get('window_bg_color') or gtk_colors.get('theme_bg_color') or '#1a1111'
                view_bg = gtk_colors.get('view_bg_color') or '#140c0c'
                fg = gtk_colors.get('window_fg_color') or gtk_colors.get('theme_fg_color') or '#f0dedd'
                sidebar_bg = gtk_colors.get('sidebar_bg_color') or gtk_colors.get('headerbar_bg_color') or '#231919'
                accent = gtk_colors.get('accent_color') or gtk_colors.get('accent_bg_color') or '#ffb3b0'
                card_bg = gtk_colors.get('card_bg_color') or gtk_colors.get('popover_bg_color') or '#3d3232'
                destr = gtk_colors.get('destructive_color') or '#ffb4ab'

                var_map['color.primary'] = accent
                var_map['color.primary.dim'] = accent
                var_map['color.primary.bright'] = accent
                var_map['color.secondary'] = accent
                var_map['color.accent'] = accent
                var_map['color.cyan'] = accent
                var_map['color.surface.darkest'] = view_bg
                var_map['color.surface.dark'] = bg
                var_map['color.surface.medium'] = sidebar_bg
                var_map['color.surface.light'] = card_bg
                var_map['color.surface.lighter'] = card_bg
                var_map['color.surface.hover'] = card_bg
                var_map['font.color'] = fg
                var_map['font.color.bright'] = fg
                var_map['outer_widget.background.color'] = bg
                var_map['inner_widget.background.color'] = view_bg
                var_map['pushbutton.background.color'] = sidebar_bg
                var_map['lineedit.background.color'] = view_bg
                var_map['focus.border.color'] = accent
                var_map['tab.font.color'] = accent
                var_map['tab.underline.color'] = accent
                var_map['progressbar.fill.color'] = accent
                var_map['console.background.color'] = view_bg

        if var_map:
            var_list = [*var_map.keys()]
            var_list.sort(key=_by_str_len, reverse=True)

            for var in var_list:
                theme_str = theme_str.replace('@' + var, var_map[var])

        if app_config:
            custom_theme = app_config.get('custom_theme') or {}
            
            if custom_theme.get('enabled', False):
                bg_color = custom_theme.get('background_color')
                text_color = custom_theme.get('text_color')
                accent_color = custom_theme.get('accent_color')
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
                    
                    custom_css += f"QToolTip {{ background-color: {bg_color or '#000'}; color: {text_color or '#fff'}; border: 1px solid {accent_color or '#555'}; }}\n"
                    
                if bg_image and os.path.exists(bg_image):
                    custom_css += f"QWidget#manage_window {{ background-image: url({bg_image}); background-position: center; background-repeat: no-repeat; }}\n"
    
                if accent_color:
                    custom_css += f"QPushButton:hover {{ border-color: {accent_color}; }}\n"
                    custom_css += f"QProgressBar::chunk {{ background-color: {accent_color}; }}\n"
                    custom_css += f"QTabBar::tab:selected {{ border-bottom: 2px solid {accent_color}; color: {accent_color}; }}\n"
                    custom_css += f"QCheckBox::indicator:checked {{ background-color: {accent_color}; border-color: {accent_color}; }}\n"
                    custom_css += f"QRadioButton::indicator:checked {{ background-color: {accent_color}; border-color: {accent_color}; }}\n"
                    custom_css += f"QSlider::handle:horizontal {{ background-color: {accent_color}; }}\n"
                    
                theme_str += custom_css

        return theme_str if not root_theme else '{}\n{}'.format(root_theme[0], theme_str), metadata


def _by_str_len(string: str) -> int:
    return len(string)


def _read_var_file(theme_file: str) -> dict:
    vars_file = theme_file.replace('.qss', '.vars')
    var_map = {}

    if os.path.isfile(vars_file):
        with open(vars_file) as f:
            for line in f.readlines():
                if line:
                    line_strip = line.strip()
                    if line_strip:
                        var_value = line_strip.split('=')

                        if var_value and len(var_value) == 2:
                            var, value = var_value[0].strip(), var_value[1].strip()

                            if var and value:
                                var_map[var] = value

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
