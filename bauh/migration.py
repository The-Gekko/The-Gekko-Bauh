"""Migración de los datos de usuario del nombre heredado al nombre propio del proyecto.

Este proyecto deriva de `bauh` y durante un tiempo compartió con él las rutas de
configuración, caché y datos (`~/.config/bauh`, `~/.cache/bauh`,
`~/.local/share/bauh`). Compartirlas provocaba dos problemas: los ajustes propios
(temas Aurora, Matugen y GTK, gems `eopkg` y `github`) contaminaban la instalación
del proyecto original, y volver a él dejaba su interfaz sin hoja de estilos.

Al adoptar un nombre propio, la primera ejecución copia los datos heredados a las
rutas nuevas. La copia es conservadora:

* solo actúa una vez: al terminar deja una marca fuera de `~/.config`, de modo que
  `--reset` no resucite los ajustes heredados en el arranque siguiente;
* solo actúa si el directorio de destino todavía no existe;
* nunca borra ni modifica el directorio de origen, de modo que el proyecto original
  sigue funcionando exactamente igual;
* de `~/.local/share` copia únicamente los temas del usuario: el resto de ese árbol
  son instalaciones (AppImage) y entornos (la gem web) que pesan cientos de megabytes
  y que, duplicados, harían que este proyecto borrase ficheros del original;
* no migra la caché, que se regenera sola y también puede ocupar cientos de megabytes;
* no actúa cuando la aplicación se ejecuta como root, porque ahí las rutas son del
  sistema (`/etc`, `/var/cache`) y su migración corresponde al empaquetador.
"""

import os
import shutil
from logging import Logger
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from bauh.api import user

# Nombre con el que el proyecto guardaba los datos antes de tener identidad propia.
LEGACY_APP_NAME = 'bauh'

# Fichero que marca la migración como hecha. Vive en `~/.local/share/<app>`, que ni `--reset`
# ni `clean_app_files` borran (solo tocan caché, configuración y temporales): así una migración
# ya realizada no se repite y el restablecimiento devuelve de verdad la configuración de fábrica.
MIGRATION_STAMP_NAME = '.migrated-from-bauh'

# Subdirectorios de `~/.local/share/<heredado>` que sí se copian. El resto se deja fuera a
# propósito: `appimage/installed` guarda los binarios instalados por el proyecto original y
# `web/env` su entorno de node/electron. Copiarlos duplicaría gigabytes y, peor, los `data.json`
# copiados conservan la ruta absoluta antigua, así que desinstalar aquí borraría los ficheros
# de la instalación original.
SHARED_SUBDIRS_TO_MIGRATE = ('themes',)


def _config_dir(app_name: str) -> str:
    return f'{Path.home()}/.config/{app_name}'


def _shared_dir(app_name: str) -> str:
    return f'{Path.home()}/.local/share/{app_name}'


def _migration_stamp(app_name: str) -> str:
    return f'{_shared_dir(app_name)}/{MIGRATION_STAMP_NAME}'


def _legacy_and_current_dirs(app_name: str) -> List[Tuple[str, str, Optional[Tuple[str, ...]]]]:
    """Tríos (origen heredado, destino actual, subdirectorios a copiar) en orden de importancia.

    Un tercer elemento a `None` significa «copiar el árbol entero».
    """
    return [
        (_config_dir(LEGACY_APP_NAME), _config_dir(app_name), None),
        (_shared_dir(LEGACY_APP_NAME), _shared_dir(app_name), SHARED_SUBDIRS_TO_MIGRATE),
    ]


def _copy_selected_subdirs(legacy_dir: str, current_dir: str, subdirs: Tuple[str, ...]) -> bool:
    """Copia solo los subdirectorios indicados. Devuelve True si se copió alguno."""
    copied = False

    for subdir in subdirs:
        legacy_subdir = os.path.join(legacy_dir, subdir)

        if not os.path.isdir(legacy_subdir):
            continue

        os.makedirs(current_dir, exist_ok=True)
        shutil.copytree(legacy_subdir, os.path.join(current_dir, subdir), symlinks=True)
        copied = True

    return copied


def _rewrite_user_theme_path(app_name: str, logger: Optional[Logger] = None) -> bool:
    """Reapunta al directorio nuevo el tema de usuario guardado como ruta absoluta.

    Los temas del usuario se identifican por su ruta completa, así que un `ui.theme` heredado
    sigue apuntando a `~/.local/share/bauh/themes/...`. Ese fichero existe, pero el índice de
    temas solo mira el directorio nuevo, de modo que la aplicación arrancaría sin hoja de
    estilos y con un simple «theme not found» en el log.
    """
    config_file = f'{_config_dir(app_name)}/config.yml'
    legacy_prefix = f'{_shared_dir(LEGACY_APP_NAME)}/'

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f.read())
    except (OSError, yaml.YAMLError):
        return False

    if not isinstance(config, dict):
        return False

    theme = (config.get('ui') or {}).get('theme')

    if not isinstance(theme, str) or not theme.startswith(legacy_prefix):
        return False

    new_theme = f'{_shared_dir(app_name)}/{theme[len(legacy_prefix):]}'

    if not os.path.isfile(new_theme):
        if logger:
            logger.warning(f"the migrated theme '{theme}' has no counterpart at '{new_theme}': "
                           f'the default theme will be used')
        return False

    config['ui']['theme'] = new_theme

    try:
        with open(config_file, 'w+') as f:
            f.write(yaml.dump(config))
    except OSError as e:
        if logger:
            logger.warning(f"could not update the theme path in '{config_file}': {e}")
        return False

    if logger:
        logger.info(f"user theme repointed from '{theme}' to '{new_theme}'")

    return True


def _write_stamp(app_name: str, logger: Optional[Logger] = None):
    stamp = _migration_stamp(app_name)

    try:
        os.makedirs(os.path.dirname(stamp), exist_ok=True)

        with open(stamp, 'w+') as f:
            f.write(f'migrated from {LEGACY_APP_NAME}\n')
    except OSError as e:
        if logger:
            logger.warning(f"could not write the migration stamp '{stamp}': {e}")


def migrate_legacy_user_data(app_name: str, logger: Optional[Logger] = None) -> List[str]:
    """Copia los datos heredados de `bauh` a las rutas de `app_name` si aún no existen.

    Devuelve la lista de directorios de destino creados. No lanza excepciones: un fallo
    de migración nunca debe impedir que la aplicación arranque, solo se registra.
    """
    if app_name == LEGACY_APP_NAME or user.is_root():
        return []

    if os.path.exists(_migration_stamp(app_name)):
        return []

    migrated = []
    failed = False

    for legacy_dir, current_dir, subdirs in _legacy_and_current_dirs(app_name):
        if os.path.exists(current_dir) or not os.path.isdir(legacy_dir):
            continue

        try:
            if subdirs is None:
                shutil.copytree(legacy_dir, current_dir, symlinks=True)
                copied = True
            else:
                copied = _copy_selected_subdirs(legacy_dir, current_dir, subdirs)

            if copied:
                migrated.append(current_dir)

                if logger:
                    logger.info(f"user data migrated from '{legacy_dir}' to '{current_dir}' "
                                f"(the original directory was left untouched)")
        except OSError as e:
            failed = True

            if logger:
                logger.warning(f"could not migrate '{legacy_dir}' to '{current_dir}': {e}")

    if migrated:
        _rewrite_user_theme_path(app_name, logger)

    if not failed:
        # la marca se escribe aunque no hubiera nada que migrar: así una instalación nueva
        # tampoco vuelve a mirar las rutas heredadas en cada arranque. Si algo falló no se
        # escribe, para poder reintentar cuando se resuelva la causa (disco lleno, permisos).
        _write_stamp(app_name, logger)

    return migrated
