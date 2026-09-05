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
"""

import os
import time
import traceback
from datetime import date, datetime
from logging import Logger
from pathlib import Path
from typing import Optional

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


def should_sync(logger: Optional[Logger] = None, reference: Optional[date] = None) -> bool:
    """Indica si toca sincronizar los repositorios.

    Se sincroniza una vez por día natural, el mismo criterio que la gem de Arch aplica a las
    bases de datos de pacman.  Una fecha futura (reloj mal puesto, arranque con la hora aún
    sin sincronizar) también obliga a sincronizar: es preferible una consulta de más que
    dejar de ver actualizaciones durante días.
    """
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
    try:
        Path(os.path.dirname(SYNC_FILE)).mkdir(parents=True, exist_ok=True)

        with open(SYNC_FILE, 'w+') as sync_file:
            sync_file.write(str(int(time.time())))
    except OSError:
        if logger:
            logger.error(f"No se pudo escribir la marca de sincronización '{SYNC_FILE}'")
            logger.error(traceback.format_exc())
