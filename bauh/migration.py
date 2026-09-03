"""Migración de los datos de usuario del nombre heredado al nombre propio del proyecto.

Este proyecto deriva de `bauh` y durante un tiempo compartió con él las rutas de
configuración, caché y datos (`~/.config/bauh`, `~/.cache/bauh`,
`~/.local/share/bauh`). Compartirlas provocaba dos problemas: los ajustes propios
(temas Aurora, Matugen y GTK, gems `eopkg` y `github`) contaminaban la instalación
del proyecto original, y volver a él dejaba su interfaz sin hoja de estilos.

Al adoptar un nombre propio, la primera ejecución copia los datos heredados a las
rutas nuevas. La copia es conservadora:

* solo actúa si el directorio de destino todavía no existe;
* nunca borra ni modifica el directorio de origen, de modo que el proyecto original
  sigue funcionando exactamente igual;
* no migra la caché, que se regenera sola y puede ocupar cientos de megabytes;
* no actúa cuando la aplicación se ejecuta como root, porque ahí las rutas son del
  sistema (`/etc`, `/var/cache`) y su migración corresponde al empaquetador.
"""

import os
import shutil
from logging import Logger
from pathlib import Path
from typing import List, Optional, Tuple

from bauh.api import user

# Nombre con el que el proyecto guardaba los datos antes de tener identidad propia.
LEGACY_APP_NAME = 'bauh'


def _legacy_and_current_dirs() -> List[Tuple[str, str]]:
    """Pares (origen heredado, destino actual) que deben migrarse, en orden de importancia.

    Se migran la configuración (ajustes, temas del usuario, listas de actualizaciones
    ignoradas) y los datos compartidos (temas instalados). La caché se omite a propósito.
    """
    home = Path.home()
    return [
        (f'{home}/.config/{LEGACY_APP_NAME}', f'{home}/.config/{{app}}'),
        (f'{home}/.local/share/{LEGACY_APP_NAME}', f'{home}/.local/share/{{app}}'),
    ]


def migrate_legacy_user_data(app_name: str, logger: Optional[Logger] = None) -> List[str]:
    """Copia los datos heredados de `bauh` a las rutas de `app_name` si aún no existen.

    Devuelve la lista de directorios de destino creados. No lanza excepciones: un fallo
    de migración nunca debe impedir que la aplicación arranque, solo se registra.
    """
    if app_name == LEGACY_APP_NAME or user.is_root():
        return []

    migrated = []

    for legacy_dir, current_pattern in _legacy_and_current_dirs():
        current_dir = current_pattern.format(app=app_name)

        if os.path.exists(current_dir) or not os.path.isdir(legacy_dir):
            continue

        try:
            shutil.copytree(legacy_dir, current_dir, symlinks=True)
            migrated.append(current_dir)

            if logger:
                logger.info(f"user data migrated from '{legacy_dir}' to '{current_dir}' "
                            f"(the original directory was left untouched)")
        except OSError as e:
            if logger:
                logger.warning(f"could not migrate '{legacy_dir}' to '{current_dir}': {e}")

    return migrated
