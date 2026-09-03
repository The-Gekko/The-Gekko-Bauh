import os
from typing import Optional

from bauh.api.paths import CONFIG_DIR, TEMP_DIR, CACHE_DIR, get_temp_dir
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ARCH_CACHE_DIR = f'{CACHE_DIR}/arch'
CATEGORIES_FILE_PATH = f'{ARCH_CACHE_DIR}/categories.txt'
GPG_SERVERS_FILE_PATH = f'{ARCH_CACHE_DIR}/gpgservers.txt'

# Punto único de configuración del origen remoto de los datos auxiliares (categorías de
# aplicaciones y servidores de claves GPG).
#
# El nombre del repositorio es literal a propósito: no debe derivarse de __app_name__,
# porque al renombrar la aplicación se construirían URL inexistentes.
#
# El proyecto NO depende de ese repositorio: lleva una copia vendorizada de ambos ficheros
# en 'resources/data' y el orden de resolución es siempre cache local -> copia vendorizada
# -> refresco remoto (ver 'bauh.gems.arch.data'). Para apuntar a un espejo propio basta con
# cambiar esta única constante.
URL_UPSTREAM_DATA_DIR = 'https://raw.githubusercontent.com/vinifmor/bauh-files/master/arch'
URL_CATEGORIES_FILE = f'{URL_UPSTREAM_DATA_DIR}/categories.txt'
URL_GPG_SERVERS = f'{URL_UPSTREAM_DATA_DIR}/gpgservers.txt'

# Copias vendorizadas que viajan con el paquete (último recurso, siempre disponible)
VENDORED_DATA_DIR = f'{ROOT_DIR}/resources/data'
VENDORED_CATEGORIES_FILE_PATH = f'{VENDORED_DATA_DIR}/categories.txt'
VENDORED_GPG_SERVERS_FILE_PATH = f'{VENDORED_DATA_DIR}/gpgservers.txt'

# Usuario del sistema sin privilegios que compila los paquetes de AUR cuando la aplicación
# se ejecuta como root. Literal por el mismo motivo que la URL anterior: renombrar la
# aplicación no debe crear un usuario nuevo ni abandonar los directorios de compilación
# del anterior.
AUR_BUILDER_USER = 'bauh-aur'

ARCH_CONFIG_DIR = f'{CONFIG_DIR}/arch'
CUSTOM_MAKEPKG_FILE = f'{ARCH_CONFIG_DIR}/makepkg.conf'
AUR_INDEX_FILE = f'{ARCH_CACHE_DIR}/aur/index.txt'
AUR_INDEX_TS_FILE = f'{ARCH_CACHE_DIR}/aur/index.ts'
CONFIG_FILE = f'{CONFIG_DIR}/arch.yml'
UPDATES_IGNORED_FILE = f'{ARCH_CONFIG_DIR}/updates_ignored.txt'
EDITABLE_PKGBUILDS_FILE = f'{ARCH_CONFIG_DIR}/aur/editable_pkgbuilds.txt'
IGNORED_REBUILD_CHECK_FILE = f'{ARCH_CONFIG_DIR}/aur/ignored_rebuild_check.txt'


def get_pkgbuild_dir(user: Optional[str] = None) -> str:
    return f'{get_temp_dir(user) if user else TEMP_DIR}/arch'


def get_icon_path() -> str:
    return resource.get_path('img/arch.svg', ROOT_DIR)


def get_repo_icon_path() -> str:
    return resource.get_path('img/repo.svg', ROOT_DIR)
