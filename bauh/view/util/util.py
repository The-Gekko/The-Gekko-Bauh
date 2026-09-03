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

    # Sin shell: el mensaje lleva el nombre del paquete, que viene del repositorio. Con
    # os.system y comillas simples, un nombre que contuviera una comilla se salía de ellas
    # y el resto se ejecutaba como una orden más.
    cmd = ['notify-send', '-a', __app_name__]

    if icon_id:
        cmd.extend(('-i', icon_id))

    cmd.append(msg)

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:  # notify-send no instalado: una notificación nunca debe tumbar nada
        logging.debug("could not notify the user: 'notify-send' is not available")


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


def get_distro() -> str:
    """Familia de la distribución, para que las gems ajusten su comportamiento.

    Solo se distingue lo que alguna gem necesita: 'arch' (que incluye los derivados que
    declaran ID_LIKE=arch, como EndeavourOS, Garuda o Manjaro) y 'solus'. El resto es
    'unknown', que no impide nada: Flatpak y las gems universales funcionan igual.
    """
    if os.path.exists('/etc/arch-release'):
        return 'arch'

    if os.path.exists('/usr/bin/eopkg') or os.path.exists('/usr/bin/eopkg4'):
        return 'solus'

    try:
        with open('/etc/os-release') as os_release_file:
            for line in os_release_file:
                if line.startswith('ID_LIKE=') and 'arch' in line:
                    return 'arch'

                if line.startswith('ID=') and line[3:].strip().strip('"') == 'solus':
                    return 'solus'
    except OSError:
        pass

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
