"""Acceso a los datos auxiliares de la gem Arch: categorias y servidores GPG.

Estos dos ficheros venian historicamente de un repositorio ajeno
(``vinifmor/bauh-files``). Para que el proyecto no se degrade si ese
repositorio desaparece o cambia, ahora se resuelven siempre en este orden:

1. Cache local descargada previamente (``~/.cache/<app>/arch/*.txt``).
2. Copia vendorizada que viaja dentro del paquete (``resources/data/*.txt``).
3. Descarga remota, que solo sirve para *refrescar* la cache.

Un fallo de red nunca deja a la aplicacion sin categorias ni sin servidores de
claves: en el peor de los casos se usa la copia vendorizada.

La URL remota vive en una unica constante (``bauh.gems.arch.URL_UPSTREAM_DATA_DIR``)
para poder apuntar a un espejo propio con una sola edicion.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from bauh.gems.arch import CATEGORIES_FILE_PATH, GPG_SERVERS_FILE_PATH, URL_GPG_SERVERS, \
    VENDORED_CATEGORIES_FILE_PATH, VENDORED_GPG_SERVERS_FILE_PATH


def parse_categories(content: Optional[str]) -> Dict[str, List[str]]:
    """Convierte el texto de un fichero de categorias en un mapa.

    Formato esperado: ``<paquete>=<Categoria>[,<Categoria>...]`` por linea.
    Se ignoran las lineas vacias, las que empiezan por '#' (cabecera de la copia
    vendorizada) y las que no tienen '='. Es deliberadamente mas tolerante que
    el analizador generico de ``bauh.commons.category`` para poder llevar una
    cabecera de procedencia en la copia vendorizada.
    """
    categories: Dict[str, List[str]] = {}

    if not content:
        return categories

    for line in content.split('\n'):
        line = line.strip()

        if not line or line.startswith('#') or '=' not in line:
            continue

        name, _, raw_categories = line.partition('=')
        name = name.strip()

        if not name:
            continue

        values = [c.strip() for c in raw_categories.split(',') if c.strip()]

        if values:
            categories[name] = values

    return categories


def parse_gpg_servers(content: Optional[str]) -> List[str]:
    """Convierte el texto de un fichero de servidores GPG en una lista ordenada.

    Un servidor por linea; se ignoran lineas vacias y comentarios ('#').
    """
    servers: List[str] = []

    if not content:
        return servers

    for line in content.split('\n'):
        line = line.strip()

        if line and not line.startswith('#') and line not in servers:
            servers.append(line)

    return servers


def _read_file(file_path: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Lee un fichero de texto y devuelve None ante cualquier problema."""
    try:
        if os.path.isfile(file_path):
            with open(file_path) as f:
                return f.read()
    except OSError:
        if logger:
            logger.error(f"Could not read the data file '{file_path}'")

    return None


def read_vendored_categories(logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
    """Categorias de la copia vendorizada que viaja con el paquete."""
    return parse_categories(_read_file(VENDORED_CATEGORIES_FILE_PATH, logger))


def read_vendored_gpg_servers(logger: Optional[logging.Logger] = None) -> List[str]:
    """Servidores GPG de la copia vendorizada que viaja con el paquete."""
    return parse_gpg_servers(_read_file(VENDORED_GPG_SERVERS_FILE_PATH, logger))


def read_categories(cache_file_path: str = CATEGORIES_FILE_PATH,
                    logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
    """Categorias disponibles: cache local descargada y, si no hay, la vendorizada."""
    cached = parse_categories(_read_file(cache_file_path, logger))

    if cached:
        return cached

    if logger:
        logger.info("No cached Arch categories available. Falling back to the vendored copy")

    return read_vendored_categories(logger)


def read_gpg_servers(cache_file_path: str = GPG_SERVERS_FILE_PATH,
                     logger: Optional[logging.Logger] = None) -> List[str]:
    """Servidores GPG disponibles: cache local descargada y, si no hay, la vendorizada."""
    cached = parse_gpg_servers(_read_file(cache_file_path, logger))

    if cached:
        return cached

    if logger:
        logger.info("No cached GPG servers available. Falling back to the vendored copy")

    return read_vendored_gpg_servers(logger)


def cache_content(content: str, cache_file_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """Guarda en disco el contenido descargado. Nunca propaga errores."""
    try:
        Path(os.path.dirname(cache_file_path)).mkdir(parents=True, exist_ok=True)

        with open(cache_file_path, 'w+') as f:
            f.write(content)

        return True
    except OSError:
        if logger:
            logger.error(f"Could not cache the downloaded data to '{cache_file_path}'")

        return False


def refresh_gpg_servers(http_client, cache_file_path: str = GPG_SERVERS_FILE_PATH,
                        url: str = URL_GPG_SERVERS,
                        logger: Optional[logging.Logger] = None) -> List[str]:
    """Intenta refrescar la cache de servidores GPG desde el origen remoto.

    Devuelve la lista descargada o una lista vacia si la descarga falla o no
    aporta nada. El llamante debe quedarse con :func:`read_gpg_servers` cuando
    esta funcion no devuelve nada.
    """
    if not http_client:
        return []

    try:
        res = http_client.get(url)
    except Exception:
        if logger:
            logger.warning(f"Could not download the GPG servers file from '{url}'")

        return []

    servers = parse_gpg_servers(res.text if res is not None else None)

    if servers:
        cache_content(content=res.text, cache_file_path=cache_file_path, logger=logger)
    elif logger:
        logger.warning(f"No GPG server could be read from '{url}'")

    return servers


def get_gpg_servers(http_client=None, cache_file_path: str = GPG_SERVERS_FILE_PATH,
                    url: str = URL_GPG_SERVERS,
                    logger: Optional[logging.Logger] = None) -> List[str]:
    """Servidores GPG a usar, garantizando que nunca se devuelve una lista vacia
    mientras exista la copia vendorizada.

    Primero se resuelve el valor local (cache -> vendorizado) para tener siempre
    una respuesta valida y despues se intenta el refresco remoto, que solo se
    impone si ha traido algo.
    """
    local_servers = read_gpg_servers(cache_file_path=cache_file_path, logger=logger)
    remote_servers = refresh_gpg_servers(http_client=http_client, cache_file_path=cache_file_path,
                                         url=url, logger=logger)

    return remote_servers if remote_servers else local_servers


def get_first_gpg_server(http_client=None, cache_file_path: str = GPG_SERVERS_FILE_PATH,
                         url: str = URL_GPG_SERVERS,
                         logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Servidor GPG preferido (el primero de la lista) o None si no hay ninguno."""
    servers = get_gpg_servers(http_client=http_client, cache_file_path=cache_file_path,
                              url=url, logger=logger)

    return servers[0] if servers else None
