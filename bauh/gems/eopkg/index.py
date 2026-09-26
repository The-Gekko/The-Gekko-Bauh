"""Estado de sincronización del índice de repositorios de Solus.

``eopkg list-upgrades`` **no consulta la red**: responde a partir del índice que ``eopkg ur``
deja en ``/var/lib/eopkg/index``.  Si nadie sincroniza, el comando contesta «No packages to
upgrade.» aunque Solus haya publicado paquetes ese mismo día, y bauh acaba afirmando que el
sistema está al día.  Este módulo lleva la cuenta de la última sincronización, igual que
``bauh/gems/arch/database.py`` hace con las bases de datos de pacman.

La «última sincronización» se resuelve como la más reciente entre dos fuentes:

* ``SYNC_FILE``: la marca que escribe bauh cuando su propia ``eopkg ur`` termina bien.
* la fecha de los ficheros de ``INDEX_DIR``: refleja cualquier ``eopkg ur`` del sistema,
  venga del instalador, del Centro de Software o de una terminal.

Mirar también el índice real evita pedir la contraseña de root nada más arrancar cuando el
sistema ya está sincronizado, y hace que una instalación nueva de bauh (todavía sin marca
propia) no fuerce una sincronización redundante.

Antes que las fechas manda, sin embargo, la comprobación remota (:func:`remote_changed`): el
mirror publica junto al índice su hash SHA-1 (``eopkg-index.xml.xz.sha1sum``, 40 bytes) y
compararlo con el índice local no necesita root.  Es la única forma fiable de ver la
sincronización semanal de Solus: con el criterio del día natural, un índice refrescado el viernes
por la mañana ocultaba hasta el sábado los paquetes publicados esa misma tarde.
"""

import hashlib
import os
import re
import time
import traceback
import urllib.request
from datetime import date, datetime
from http.client import HTTPException
from logging import Logger
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from bauh.gems.eopkg import EOPKG_CACHE_DIR

# marca de tiempo de la última 'eopkg ur' lanzada por bauh
SYNC_FILE = f'{EOPKG_CACHE_DIR}/repo_sync'

# donde eopkg deja los índices descargados (un subdirectorio por repositorio)
INDEX_DIR = '/var/lib/eopkg/index'

# sólo los ficheros del índice propiamente dicho ('eopkg-index.xml.xz', su '.sha1sum' y el
# '.xml' descomprimido) prueban una descarga terminada; el resto del directorio no sirve
INDEX_FILE_PREFIX = 'eopkg-index'

# eopkg descarga a un fichero aparte y lo renombra al terminar (pisi/constants.py:
# partial_suffix = '.part', temporary_suffix = '.tmp'): un parcial es justo la señal de que
# la descarga NO terminó
PARTIAL_SUFFIXES = ('.part', '.tmp')

# margen de tolerancia para las marcas futuras del índice (ver :func:`_index_date`)
CLOCK_SKEW_TOLERANCE = 86400.0

# fichero de cada repositorio con la dirección de su índice ('uri + ".sha1sum"' es el hash remoto,
# igual que en pisi/file.py)
URI_FILE = 'uri'
SHA1SUM_SUFFIX = '.sha1sum'
RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

# segundos máximos para descargar el hash remoto: sin red o con el mirror caído la comprobación
# queda como desconocida y manda el criterio del día natural
REMOTE_TIMEOUT = 10

# el arranque pregunta varias veces seguidas (requires_root, la tarea de sincronización y
# list_warnings): durante este margen se reutiliza la respuesta en lugar de volver a la red
REMOTE_CACHE_TTL = 60

_remote_cache: Optional[Tuple[float, Optional[bool]]] = None


def _sync_file_date(logger: Optional[Logger] = None) -> Optional[datetime]:
    """Momento de la última sincronización registrada por bauh, o ``None``."""
    if not os.path.exists(SYNC_FILE):
        return None

    try:
        with open(SYNC_FILE) as sync_file:
            return datetime.fromtimestamp(int(sync_file.read().strip()))
    except (OSError, OverflowError, ValueError):
        # OverflowError, no ValueError, es lo que lanza 'fromtimestamp' con una marca
        # absurda ('99999999999999999999'); sin capturarla la excepción sube hasta
        # 'requires_root(PREPARE)' y rompe el arranque entero
        if logger:
            logger.warning(f"No se pudo leer la marca de sincronización '{SYNC_FILE}'")
        return None


def _index_date(logger: Optional[Logger] = None) -> Optional[datetime]:
    """Momento del último ``eopkg ur`` del sistema, según los ficheros del índice.

    Sólo cuentan los ficheros que empiezan por :data:`INDEX_FILE_PREFIX`, que son los que
    eopkg escribe DESPUÉS de una descarga correcta.  El resto del directorio no prueba nada:
    ``uri`` se reescribe ANTES de intentar la descarga (``pisi/index.py``,
    ``read_uri_of_repo``), así que un ``eopkg ur`` que se cae por falta de red o por un
    mirror caído lo deja con la fecha de hoy y haría pasar por buena una sincronización que
    nunca ocurrió: ni se avisaría del índice viejo ni se reintentaría hasta el día siguiente.
    Los parciales de una descarga a medias (:data:`PARTIAL_SUFFIXES`) se descartan por lo
    mismo.

    También se ignoran las marcas muy futuras: un arranque anterior con el reloj mal puesto
    puede dejar el índice fechado en el futuro, y eso obligaría a pedir la contraseña y
    sincronizar en cada arranque, además de anunciar un índice «desfasado» con una fecha que
    aún no ha llegado.  Se tolera un día de margen para no penalizar husos horarios ni
    relojes con una desviación pequeña.
    """
    if not os.path.isdir(INDEX_DIR):
        return None

    newest = 0.0
    limit = time.time() + CLOCK_SKEW_TOLERANCE

    try:
        for parent, _, file_names in os.walk(INDEX_DIR):
            for file_name in file_names:
                if not file_name.startswith(INDEX_FILE_PREFIX):
                    continue

                if file_name.endswith(PARTIAL_SUFFIXES):
                    continue

                try:
                    moment = os.path.getmtime(os.path.join(parent, file_name))
                except OSError:  # el fichero desaparece si eopkg está sincronizando ahora mismo
                    continue

                if moment > limit:
                    if logger:
                        logger.warning(f"Se ignora la fecha futura del índice "
                                       f"'{os.path.join(parent, file_name)}'")
                    continue

                newest = max(newest, moment)
    except OSError:
        if logger:
            logger.warning(f"No se pudo inspeccionar el índice de repositorios '{INDEX_DIR}'")
        return None

    if not newest:
        return None

    try:
        return datetime.fromtimestamp(newest)
    except (OSError, OverflowError, ValueError):
        # una marca corrupta del sistema de ficheros no puede tumbar el arranque
        if logger:
            logger.warning(f"El índice de repositorios '{INDEX_DIR}' tiene una fecha ilegible")
        return None


def last_sync(logger: Optional[Logger] = None) -> Optional[datetime]:
    """La más reciente entre la marca de bauh y la fecha del índice de eopkg."""
    dates = [moment for moment in (_sync_file_date(logger), _index_date(logger)) if moment]
    return max(dates) if dates else None


def _repositories() -> List[Tuple[str, str]]:
    """``(directorio, uri)`` de cada repositorio con índice en :data:`INDEX_DIR`."""
    try:
        names = sorted(os.listdir(INDEX_DIR))
    except OSError:
        return []

    repos = []

    for name in names:
        repo_dir = os.path.join(INDEX_DIR, name)

        try:
            with open(os.path.join(repo_dir, URI_FILE)) as uri_file:
                uri = uri_file.read().strip()
        except OSError:
            continue

        if uri:
            repos.append((repo_dir, uri))

    return repos


def _local_sha1(repo_dir: str, uri: str) -> Optional[str]:
    """SHA-1 del índice descargado, calculado sobre el propio fichero.

    Es lo mismo que compara eopkg (``pisi/file.py``).  El ``.sha1sum`` guardado no sirve: eopkg lo
    reescribe ANTES de descargar el índice, así que tras una descarga cortada ya lleva el hash
    nuevo aunque el índice siga siendo el viejo.
    """
    digest = hashlib.sha1()

    try:
        with open(os.path.join(repo_dir, os.path.basename(urlparse(uri).path)), 'rb') as index_file:
            for chunk in iter(lambda: index_file.read(1 << 20), b''):
                digest.update(chunk)
    except OSError:  # nunca se ha descargado
        return None

    return digest.hexdigest()


def _remote_sha1(uri: str, timeout: float) -> Optional[str]:
    """Hash que publica el mirror para el índice de ``uri``; ``None`` si no se puede saber."""
    scheme = urlparse(uri).scheme

    if not scheme:  # repositorio local, dado como ruta
        url = Path(uri).absolute().as_uri() + SHA1SUM_SUFFIX
    elif scheme in ('http', 'https', 'file'):
        url = uri + SHA1SUM_SUFFIX
    else:
        return None

    with urllib.request.urlopen(url, timeout=timeout) as response:
        words = response.read(1024).decode('ascii', errors='ignore').split()

    sha1 = words[0].lower() if words else ''
    return sha1 if RE_SHA1.match(sha1) else None


def remote_changed(logger: Optional[Logger] = None, timeout: float = REMOTE_TIMEOUT) -> Optional[bool]:
    """Indica si algún repositorio ha publicado un índice distinto del que hay en el sistema.

    No necesita root: basta con leer el índice local y descargar el hash remoto.  Devuelve
    ``True`` si algún mirror publica un índice nuevo, ``False`` si todos coinciden con el local
    (``eopkg ur`` no descargaría nada) y ``None`` si no se pudo comprobar (sin red, mirror caído,
    ningún repositorio configurado).
    """
    global _remote_cache

    if _remote_cache and time.monotonic() - _remote_cache[0] < REMOTE_CACHE_TTL:
        return _remote_cache[1]

    repos = _repositories()
    result = False if repos else None

    for repo_dir, uri in repos:
        try:
            remote = _remote_sha1(uri, timeout)
        except (OSError, ValueError, HTTPException):
            remote = None

        if remote is None:
            if logger:
                logger.info(f"No se pudo consultar el hash del índice remoto '{uri}'")

            result = None
            continue

        if remote != _local_sha1(repo_dir, uri):
            if logger:
                logger.info(f"El repositorio '{os.path.basename(repo_dir)}' ha publicado un índice nuevo")

            result = True
            break

    _remote_cache = (time.monotonic(), result)
    return result


def forget_remote_check():
    """Descarta la última comprobación remota: tras un ``eopkg ur`` ya no vale."""
    global _remote_cache
    _remote_cache = None


def should_sync(logger: Optional[Logger] = None, reference: Optional[date] = None,
                check_remote: bool = True) -> bool:
    """Indica si toca sincronizar los repositorios.

    Manda la comprobación remota (:func:`remote_changed`): se sincroniza cuando Solus ha
    publicado un índice nuevo, a cualquier hora, y no se molesta al usuario cuando el índice
    local ya es idéntico al del mirror.  Sólo si no se puede comprobar (sin red) se vuelve al
    criterio de una vez por día natural, el mismo que la gem de Arch aplica a las bases de
    datos de pacman.  Una fecha futura (reloj mal puesto, arranque con la hora aún sin
    sincronizar) también obliga a sincronizar: es preferible una consulta de más que dejar de
    ver actualizaciones durante días.
    """
    if check_remote:
        changed = remote_changed(logger)

        if changed is not None:
            if logger:
                logger.info("El índice de los repositorios de eopkg " +
                            ("está desfasado respecto al mirror" if changed else "coincide con el del mirror"))

            return changed

    moment = last_sync(logger)

    if moment is None:
        if logger:
            logger.info("Los repositorios de eopkg no se han sincronizado nunca")
        return True

    today = reference if reference else date.today()

    if moment.date() == today:
        if logger:
            logger.info("Los repositorios de eopkg ya están sincronizados")
        return False

    if logger:
        logger.info(f"La sincronización de los repositorios de eopkg está desfasada "
                    f"(última: {moment.isoformat(sep=' ', timespec='seconds')})")

    return True


def register_sync(logger: Optional[Logger] = None):
    """Anota que los repositorios acaban de sincronizarse."""
    forget_remote_check()

    try:
        Path(os.path.dirname(SYNC_FILE)).mkdir(parents=True, exist_ok=True)

        with open(SYNC_FILE, 'w+') as sync_file:
            sync_file.write(str(int(time.time())))
    except OSError:
        if logger:
            logger.error(f"No se pudo escribir la marca de sincronización '{SYNC_FILE}'")
            logger.error(traceback.format_exc())
