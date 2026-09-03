import os

from bauh.api.paths import CONFIG_DIR, CACHE_DIR
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAP_CACHE_DIR = f'{CACHE_DIR}/snap'
CONFIG_FILE = f'{CONFIG_DIR}/snap.yml'
CATEGORIES_FILE_PATH = f'{SNAP_CACHE_DIR}/categories.txt'
# Host de los ficheros de datos (categorías, sugerencias). Centralizado para poder cambiarlo de sitio en el futuro.
URL_BAUH_FILES = 'https://raw.githubusercontent.com/vinifmor/bauh-files/master'
URL_CATEGORIES_FILE = f'{URL_BAUH_FILES}/snap/categories.txt'
URL_SUGGESTIONS_FILE = f'{URL_BAUH_FILES}/snap/suggestions.txt'


def get_icon_path() -> str:
    return resource.get_path('img/snap.svg', ROOT_DIR)
