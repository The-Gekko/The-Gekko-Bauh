"""Restos de la antigua gem «web» (aplicaciones web empaquetadas con nativefier).

La gem se retiró: nativefier está archivado desde septiembre de 2023 y cada app web
llevaba un Electron que ya no recibe parches de seguridad. Las apps que alguien
instalara siguen arrancando, pero bauh ya no puede gestionarlas. Este módulo solo
las encuentra, avisa de ellas al arrancar y las borra cuando se le pide con
`gekko-bauh-cli clean-web-apps`.
"""
import glob
import os
import shutil
from typing import List, Optional

from bauh.api.paths import AUTOSTART_DIR, CACHE_DIR, CONFIG_DIR, DESKTOP_ENTRIES_DIR, SHARED_FILES_DIR
from bauh.view.util.translation import I18n

WEB_DIR = f'{SHARED_FILES_DIR}/web'
INSTALLED_DIR = f'{WEB_DIR}/installed'
WEB_CACHE_DIR = f'{CACHE_DIR}/web'
WEB_CONFIG_FILE = f'{CONFIG_DIR}/web.yml'
# Prefijo fijo de la gem (no dependía de __app_name__): lo llevan tanto la entrada de
# menú como el autoarranque de cada app, que comparten nombre de fichero.
DESKTOP_PREFIX = 'bauh.web.'
CLEAN_COMMAND = 'gekko-bauh-cli clean-web-apps'


def _desktop_files(directory: str) -> List[str]:
    return sorted(glob.glob(os.path.join(directory, f'{DESKTOP_PREFIX}*.desktop')))


def installed_apps() -> List[str]:
    """Nombres de las apps web que quedan instaladas (carpeta o entrada de menú)."""
    names = set()

    if os.path.isdir(INSTALLED_DIR):
        names.update(d for d in os.listdir(INSTALLED_DIR) if os.path.isdir(os.path.join(INSTALLED_DIR, d)))

    for path in _desktop_files(DESKTOP_ENTRIES_DIR):
        names.add(os.path.basename(path)[len(DESKTOP_PREFIX):-len('.desktop')])

    return sorted(names)


def leftovers() -> List[str]:
    """Todo lo que dejó la gem: apps, entorno (node, Electron), caché, ajustes y accesos directos."""
    paths = [p for p in (WEB_DIR, WEB_CACHE_DIR, WEB_CONFIG_FILE) if os.path.lexists(p)]
    paths.extend(_desktop_files(DESKTOP_ENTRIES_DIR))
    paths.extend(_desktop_files(AUTOSTART_DIR))
    return paths


def remove() -> List[str]:
    """Borra todos los restos y devuelve los que no se pudieron borrar."""
    failed = []

    for path in leftovers():
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError:
            failed.append(path)

    return failed


def warning(i18n: I18n) -> Optional[str]:
    """Aviso para el arranque mientras quede alguna app web, o None."""
    apps = installed_apps()

    if not apps:
        return None

    return i18n['web_legacy.warning'].format(apps=', '.join(apps), command=CLEAN_COMMAND)
