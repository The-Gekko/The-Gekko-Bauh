import logging
import os
import shutil
import subprocess
import sys
from functools import lru_cache
from typing import List, Tuple

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QIcon
from colorama import Fore

from bauh import __app_name__
from bauh.api.abstract.controller import SoftwareManager
from bauh.api.paths import CONFIG_DIR, CACHE_DIR, TEMP_DIR
from bauh.commons.system import run_cmd
from bauh.view.util import resource


def notify_user(msg: str, icon_path: str = None):
    icon_id = icon_path

    if not icon_id:
        icon_id = get_default_icon()[0]

    os.system("notify-send -a {} {} '{}'".format(__app_name__, "-i {}".format(icon_id) if icon_id else '', msg))


@lru_cache(maxsize=8)
def _cached_icon(path: str) -> QIcon:
    """Cachea el QIcon por ruta: decodificar el PNG en cada dialogo es caro."""
    return QIcon(path)


def get_default_icon(system: bool = True) -> Tuple[str, QIcon]:
    # el icono instalado en el tema del sistema tiene prioridad cuando se solicita ('Icon=bauh' de los .desktop)
    if system:
        system_icon = QIcon.fromTheme(__app_name__)
        if not system_icon.isNull():
            return system_icon.name(), system_icon

    path = resource.get_path('img/gekko-bauh.png')
    return path, _cached_icon(path)


def restart_app():
    appimage_path = os.getenv('APPIMAGE')

    if appimage_path:
        restart_cmd = [appimage_path]
    else:
        # se relanza como modulo para que el paquete 'bauh' se resuelva sin depender del directorio actual
        restart_cmd = [sys.executable, '-m', 'bauh.app', *sys.argv[1:]]

    # start_new_session desliga el proceso nuevo del grupo de procesos que esta muriendo
    subprocess.Popen(restart_cmd, start_new_session=True)
    QCoreApplication.exit()


def get_distro():
    if os.path.exists('/etc/arch-release'):
        return 'arch'

    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release', 'r') as os_release_file:
            for line in os_release_file:
                if 'ID_LIKE=arch' in line:
                    return 'arch'

    if os.path.exists('/proc/version'):
        if 'ubuntu' in run_cmd('cat /proc/version').lower():
            return 'ubuntu'

    return 'unknown'


def clean_app_files(managers: List[SoftwareManager], logs: bool = True):

    if logs:
        print(f'[{__app_name__}] Cleaning configuration and cache files')

    for path in (CACHE_DIR, CONFIG_DIR, TEMP_DIR):
        if logs:
            print(f'[{__app_name__}] Deleting directory {path}')

        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                if logs:
                    print(f'{Fore.YELLOW}[{__app_name__}] Directory {path} deleted{Fore.RESET}')
            except Exception:
                if logs:
                    print(f'{Fore.RED}[{__app_name__}] An exception has happened when '
                          f'deleting {path}{Fore.RESET}')
                    logging.error("Exception occurred", exc_info=True)

    if managers:
        for m in managers:
            m.clear_data()

    if logs:
        print(f'[{__app_name__}] Cleaning finished')
