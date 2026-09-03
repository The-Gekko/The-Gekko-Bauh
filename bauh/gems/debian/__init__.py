import os

from bauh.api.paths import CACHE_DIR, CONFIG_DIR
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DEBIAN_CACHE_DIR = f'{CACHE_DIR}/debian'
APP_INDEX_FILE = f'{DEBIAN_CACHE_DIR}/apps_idx.json'
CONFIG_FILE = f'{CONFIG_DIR}/debian.yml'
PACKAGE_SYNC_TIMESTAMP_FILE = f'{DEBIAN_CACHE_DIR}/sync_pkgs.ts'
DEBIAN_ICON_PATH = resource.get_path('img/debian.svg', ROOT_DIR)
# Host de los ficheros de datos (sugerencias). Centralizado para poder cambiarlo de sitio en el futuro.
URL_BAUH_FILES = 'https://raw.githubusercontent.com/vinifmor/bauh-files/master'
URL_SUGGESTIONS_FILE = f'{URL_BAUH_FILES}/debian/suggestions_v1.txt'
