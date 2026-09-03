import logging
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple

from bauh import __display_name__, __version__
from bauh.api.http import HttpClient
from bauh.api.paths import CACHE_DIR
from bauh.commons.html import bold, link
from bauh.view.util.translation import I18n

# Repositorio del fork cuyos releases se consultan. El upstream (vinifmor/bauh) comparte el mismo esquema
# numérico de versiones, así que avisar de sus releases llevaría al usuario a sustituir el fork por el original.
FORK_REPOSITORY = 'The-Gekko/Bauh-Fork-The-Gekko'
RELEASES_URL = f'https://api.github.com/repos/{FORK_REPOSITORY}/releases'

# Etiqueta git del fork: 'v<X.Y.Z>-gekko.<N>' (equivale a la versión PEP 440 '<X.Y.Z>+gekko.<N>' de bauh/__init__.py).
# Las etiquetas sin sufijo gekko (p. ej. la histórica 'v0.10.7') se aceptan y cuentan como N = 0, es decir,
# anteriores a cualquier '-gekko.N' de la misma base.
RE_RELEASE_TAG = re.compile(r'^v?(\d+(?:\.\d+)*)(?:-gekko\.(\d+))?$')
RE_APP_VERSION = re.compile(r'^(\d+(?:\.\d+)*)(?:\+gekko\.(\d+))?$')

# (base numérica, número de revisión gekko)
VersionKey = Tuple[Tuple[int, ...], int]


def _parse(pattern: re.Pattern, text: Optional[str]) -> Optional[VersionKey]:
    if not text or not isinstance(text, str):
        return None

    match = pattern.match(text.strip())

    if not match:
        return None

    base = tuple(int(part) for part in match.group(1).split('.'))
    revision = int(match.group(2)) if match.group(2) is not None else 0
    return base, revision


def parse_release_tag(tag: Optional[str]) -> Optional[VersionKey]:
    """
    Convierte una etiqueta de release del fork ('v0.10.8-gekko.2', 'v0.10.7', '0.10.7') en una clave comparable.
    Devuelve None si la etiqueta no sigue la convención.
    """
    return _parse(RE_RELEASE_TAG, tag)


def parse_app_version(version: Optional[str]) -> Optional[VersionKey]:
    """
    Convierte la versión PEP 440 de la aplicación ('0.10.8+gekko.1' o simplemente '0.10.8') en una clave comparable.
    Devuelve None si no se reconoce el formato.
    """
    return _parse(RE_APP_VERSION, version)


def is_newer_release(tag: Optional[str], current_version: Optional[str] = None) -> bool:
    """
    Indica si la etiqueta 'tag' corresponde a una versión posterior a la versión en ejecución.
    Si alguna de las dos no se puede interpretar, se considera que no hay actualización.
    """
    release_key = parse_release_tag(tag)
    current_key = parse_app_version(__version__ if current_version is None else current_version)

    if release_key is None or current_key is None:
        return False

    return release_key > current_key


def find_latest_release(releases: Iterable[dict]) -> Optional[dict]:
    """
    Devuelve el release publicado (ni borrador ni prelanzamiento) con la etiqueta más alta según la convención del
    fork. Los releases con etiquetas no reconocidas se ignoran.
    """
    latest, latest_key = None, None

    for release in releases or ():
        if not isinstance(release, dict) or release.get('draft') or release.get('prerelease'):
            continue

        key = parse_release_tag(release.get('tag_name'))

        if key is None:
            continue

        if latest_key is None or key > latest_key:
            latest, latest_key = release, key

    return latest


def check_for_update(logger: logging.Logger, http_client: HttpClient, i18n: I18n, tray: bool = False) -> Optional[str]:
    """
    Consulta los releases del fork y devuelve el aviso de actualización (o None si no hay una versión más reciente).

    :param logger:
    :param http_client:
    :param i18n:
    :param tray: si el aviso se generará para la bandeja del sistema (afecta al texto y al fichero de notificación)
    """
    logger.info("Checking for updates")

    try:
        releases = http_client.get_json(RELEASES_URL)

        if releases:
            latest = find_latest_release(releases)

            if latest and latest.get('tag_name'):
                tag_name = latest['tag_name']
                notifications_dir = f'{CACHE_DIR}/updates'
                release_file = f"{notifications_dir}/{'tray_' if tray else ''}{tag_name}"

                if os.path.exists(release_file):
                    logger.info("Release {} already notified".format(tag_name))
                elif is_newer_release(tag_name):
                    try:
                        Path(notifications_dir).mkdir(parents=True, exist_ok=True)
                        with open(release_file, 'w+') as f:
                            f.write('')
                    except Exception:
                        logger.error("An error occurred while trying to create the update notification file: {}".format(release_file))

                    if tray:
                        # se usa el nombre visible, no el identificador técnico: es texto para el usuario
                        return i18n['tray.warning.update_available'].format(__display_name__, tag_name)
                    else:
                        return i18n['warning.update_available'].format(bold(__display_name__), bold(tag_name),
                                                                      link(latest.get('html_url', '?')))
                else:
                    logger.info("No updates available")
            else:
                logger.warning("No official release found")
        else:
            logger.warning("No releases returned from the GitHub API")
    except Exception:
        logger.error("An error occurred while trying to retrieve the current releases")
