import os

from bauh.api.paths import DESKTOP_ENTRIES_DIR, CONFIG_DIR, TEMP_DIR, CACHE_DIR, SHARED_FILES_DIR
from bauh.commons import resource
from bauh.commons.util import map_timestamp_file

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_SHARED_DIR = f'{SHARED_FILES_DIR}/web'
WEB_CACHE_DIR = f'{CACHE_DIR}/web'
INSTALLED_PATH = f'{WEB_SHARED_DIR}/installed'
ENV_PATH = f'{WEB_SHARED_DIR}/env'
FIX_FILE_PATH = WEB_SHARED_DIR + '/fixes/{electron_branch}/{app_id}.js'
NODE_DIR_PATH = f'{ENV_PATH}/node'
NODE_PATHS = {f'{NODE_DIR_PATH}/bin'}
NODE_BIN_PATH = f'{NODE_DIR_PATH}/bin/node'
NPM_BIN_PATH = f'{NODE_DIR_PATH}/bin/npm'
NODE_MODULES_PATH = f'{ENV_PATH}/node_modules'
NATIVEFIER_BIN_PATH = f'{NODE_MODULES_PATH}/.bin/nativefier'
ELECTRON_CACHE_DIR = f'{ENV_PATH}/electron'
# Host de los ficheros de datos (entorno, parches, sugerencias). Centralizado para poder cambiarlo de sitio en el futuro.
URL_BAUH_FILES = 'https://raw.githubusercontent.com/vinifmor/bauh-files/master'
URL_ENVIRONMENT_SETTINGS = f'{URL_BAUH_FILES}/web/env/v2/environment.yml'
URL_SUGGESTIONS_FILE = f'{URL_BAUH_FILES}/web/env/v2/suggestions.yml'
# Prefijo literal y estable de las entradas de escritorio de las aplicaciones web. No se
# deriva de __app_name__: al renombrar la aplicación, las entradas ya instaladas dejarían
# de encontrarse y quedarían huérfanas en el menú del usuario.
DESKTOP_ENTRY_PREFIX = 'bauh.web'
DESKTOP_ENTRY_PATH_PATTERN = f'{DESKTOP_ENTRIES_DIR}/{DESKTOP_ENTRY_PREFIX}.' + '{name}.desktop'
URL_FIX_PATTERN = URL_BAUH_FILES + "/web/env/v2/fix/{domain}/{electron_branch}/fix.js"
URL_PROPS_PATTERN = URL_BAUH_FILES + "/web/env/v2/fix/{domain}/{electron_branch}/properties"
# User-Agent de un Chrome reciente (formato reducido 'major.0.0.0' que usa Chrome desde la v101):
# muchos sitios sirven desafíos o versiones degradadas a navegadores de hace años.
UA_CHROME = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
# Comando sugerido cuando faltan las dependencias Python de la gem (nombres PyPI, no de paquetes de distro)
PIPX_INJECT_COMMAND = 'pipx inject bauh-gekko beautifulsoup4 lxml'
TEMP_PATH = f'{TEMP_DIR}/web'
SEARCH_INDEX_FILE = f'{WEB_CACHE_DIR}/index.yml'
CONFIG_FILE = f'{CONFIG_DIR}/web.yml'
ENVIRONMENT_SETTINGS_CACHED_FILE = f'{WEB_CACHE_DIR}/environment.yml'
ENVIRONMENT_SETTINGS_TS_FILE = f'{WEB_CACHE_DIR}/environment.ts'


def get_icon_path() -> str:
    return resource.get_path('img/web.svg', ROOT_DIR)
