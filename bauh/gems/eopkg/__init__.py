import os

from bauh.api.paths import CACHE_DIR, CONFIG_DIR
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
EOPKG_CACHE_DIR = f'{CACHE_DIR}/eopkg'
CONFIG_FILE = f'{CONFIG_DIR}/eopkg.yml'


def get_icon_path() -> str:
    return resource.get_path('img/eopkg.svg', ROOT_DIR)
