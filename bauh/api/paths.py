import os
import stat
import tempfile
from functools import lru_cache
from getpass import getuser
from pathlib import Path
from typing import Optional

from bauh import __app_name__
from bauh.api import user


def is_private_dir(path: str) -> bool:
    """Indica si 'path' es un directorio real (no un enlace simbólico) del usuario actual
    sin permisos de acceso para grupo u otros."""
    try:
        st = os.lstat(path)
    except OSError:
        return False

    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and (st.st_mode & 0o077) == 0


def ensure_private_dir(path: str) -> bool:
    """Crea 'path' con modo 0700 (o lo valida si ya existe) y devuelve si es seguro usarlo.

    Se rechaza si es un enlace simbólico, si no es un directorio, si pertenece a otro usuario
    o si no puede crearse ni ajustarse su modo.
    """
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
        st = os.lstat(path)

        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
            return False

        if st.st_mode & 0o077:
            os.chmod(path, 0o700)

        return True
    except OSError:
        return False


def resolve_private_temp_dir(preferred: str) -> str:
    """Devuelve 'preferred' si puede garantizarse como directorio privado del usuario (modo 0700, sin
    enlace simbólico ni otro dueño); si no, crea un directorio aleatorio 0700 con tempfile.mkdtemp.
    Como último recurso (p. ej. sin espacio en disco) devuelve 'preferred' sin garantías."""
    if ensure_private_dir(preferred):
        return preferred

    try:
        return tempfile.mkdtemp(prefix=f'{__app_name__}-')
    except OSError:
        return preferred


CACHE_DIR = f'/var/cache/{__app_name__}' if user.is_root() else f'{Path.home()}/.cache/{__app_name__}'
CONFIG_DIR = f'/etc/{__app_name__}' if user.is_root() else f'{Path.home()}/.config/{__app_name__}'
USER_THEMES_DIR = f'/usr/share/{__app_name__}/themes' if user.is_root() else f'{Path.home()}/.local/share/{__app_name__}/themes'
DESKTOP_ENTRIES_DIR = '/usr/share/applications' if user.is_root() else f'{Path.home()}/.local/share/applications'

_CURRENT_USER = getuser()


@lru_cache(maxsize=1)
def _current_user_temp_dir() -> str:
    return resolve_private_temp_dir(f'{CACHE_DIR}/tmp')


def get_temp_dir(username: Optional[str] = None) -> str:
    """Directorio temporal privado del usuario indicado (por defecto, el actual).

    Para el usuario actual se usa '<caché>/tmp' (~/.cache/bauh/tmp, o /var/cache/bauh/tmp como root),
    creado con modo 0700 y verificado (dueño y ausencia de enlace simbólico), en lugar del antiguo
    '/tmp/bauh@usuario': una ruta predecible en un directorio compartido que otro usuario local podía
    crear de antemano para controlar los paquetes que root instala o los AppImage que se ejecutan.
    Si no puede garantizarse, se recurre a un directorio aleatorio 0700 (ver resolve_private_temp_dir).
    No se usa $XDG_RUNTIME_DIR porque es un tmpfs pequeño (10 % de la RAM) inadecuado para
    compilaciones AUR y descargas de varios cientos de MB.

    Para otro usuario (p. ej. el usuario constructor de paquetes AUR cuando bauh corre como root) se
    mantiene la ruta histórica '/tmp/<app>@<usuario>', pues es dicho usuario quien debe poder crearla.
    """
    if username and username != _CURRENT_USER:
        return f'/tmp/{__app_name__}@{username}'

    return _current_user_temp_dir()


TEMP_DIR = get_temp_dir(_CURRENT_USER)
LOGS_DIR = f'{CACHE_DIR}/logs'
AUTOSTART_DIR = '/etc/xdg/autostart' if user.is_root() else f'{Path.home()}/.config/autostart'
BINARIES_DIR = '/usr/local/bin' if user.is_root() else f'{Path.home()}/.local/bin'
SHARED_FILES_DIR = f'/usr/local/share/{__app_name__}' if user.is_root() else f'{Path.home()}/.local/share/{__app_name__}'
