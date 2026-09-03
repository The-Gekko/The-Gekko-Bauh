import os

from bauh.api.paths import CACHE_DIR, CONFIG_DIR, SHARED_FILES_DIR
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# datos de la gem bajo XDG (~/.local/share/bauh/github) en lugar de ~/BauhRepos
GITHUB_SHARED_DIR = f'{SHARED_FILES_DIR}/github'
DEFAULT_REPOS_DIR = f'{GITHUB_SHARED_DIR}/repos'

# ubicación heredada: se sigue reconociendo para no perder los clones de instalaciones previas
LEGACY_REPOS_DIR = os.path.join(os.path.expanduser('~'), 'BauhRepos')

CONFIG_FILE = f'{CONFIG_DIR}/github.yml'
GITHUB_CACHE_DIR = f'{CACHE_DIR}/github'

# registro de lo que la gem ha construido e instalado fuera del clon (paquetes pacman,
# aplicaciones de pipx, binarios de cargo), necesario para poder desinstalarlo después
INSTALLED_FILE = f'{GITHUB_CACHE_DIR}/installed.json'


def get_icon_path() -> str:
    return resource.get_path('img/github.svg', ROOT_DIR)
