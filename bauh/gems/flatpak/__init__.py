import os
from pathlib import Path

from bauh.api import user
from bauh.api.paths import CONFIG_DIR
from bauh.commons import resource
from bauh.commons.version_util import map_str_version

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = f'{CONFIG_DIR}/flatpak.yml'
FLATPAK_CONFIG_DIR = f'{CONFIG_DIR}/flatpak'
UPDATES_IGNORED_FILE = f'{FLATPAK_CONFIG_DIR}/updates_ignored.txt'
EXPORTS_PATH = '/usr/share/flatpak/exports/share' if user.is_root() else f'{Path.home()}/.local/share/flatpak/exports/share'
VERSION_1_2 = map_str_version("1.2")
VERSION_1_3 = map_str_version("1.3")
VERSION_1_4 = map_str_version("1.4")
VERSION_1_5 = map_str_version("1.5")
VERSION_1_12 = map_str_version("1.12")
# Host de los ficheros de datos (sugerencias). Centralizado para poder cambiarlo de sitio en el futuro.
URL_BAUH_FILES = 'https://raw.githubusercontent.com/vinifmor/bauh-files/master'
URL_SUGGESTIONS_FILE = f'{URL_BAUH_FILES}/flatpak/suggestions.txt'


def get_icon_path() -> str:
    return resource.get_path('img/flatpak.svg', ROOT_DIR)
