"""Heuristica para reconocer variantes de un mismo programa en AUR.

En AUR es habitual que un mismo programa se publique varias veces con el mismo
nombre base y un sufijo convencional:

* ``foo``      -> receta que compila la version estable desde las fuentes
* ``foo-bin``  -> variante precompilada (binario publicado por el autor)
* ``foo-git``  -> variante de desarrollo que sigue la rama principal del VCS

HEURISTICA EXACTA
-----------------
Se considera variante todo nombre que termine en ``-<sufijo>`` donde ``<sufijo>``
pertenece a una de estas dos listas cerradas:

* :data:`BINARY_SUFFIXES` (``bin``)          -> variante precompilada
* :data:`DEVELOPMENT_SUFFIXES` (``git``, ``svn``, ``hg``, ``bzr``, ``cvs``,
  ``nightly``)                               -> variante de desarrollo

El nombre base es el nombre sin ese sufijo y debe tener al menos
:data:`MIN_BASE_LENGTH` caracteres. Solo se recorta **un** sufijo: ``foo-bin-git``
se reduce a ``foo-bin``, no a ``foo``.

LIMITES CONOCIDOS
-----------------
* Es una heuristica puramente lexica: no consulta AUR ni los repositorios, asi
  que no puede saber si el paquete base existe realmente. Por eso el llamante
  debe corroborar la existencia del base antes de mostrar la anotacion al
  usuario (ver ``ArchManager.search``).
* Produce falsos positivos con paquetes cuyo nombre termina legitimamente en uno
  de los sufijos sin ser una variante (por ejemplo un hipotetico ``python-git``
  que fuese una biblioteca y no la version de desarrollo de ``python``). Por eso
  la anotacion no cambia el nombre del paquete ni lo elimina de los resultados.
* No reconoce sufijos menos habituales (``-nightly-bin``, ``-appimage``,
  ``-electron``, ``-beta``...) ni prefijos de proveedor (``lib32-``).
"""

from typing import Dict, Iterable, List, Optional, Tuple

# Sufijos que identifican una variante precompilada
BINARY_SUFFIXES = ('bin',)

# Sufijos que identifican una variante de desarrollo (sigue el control de versiones)
DEVELOPMENT_SUFFIXES = ('git', 'svn', 'hg', 'bzr', 'cvs', 'nightly')

# Tipos de variante expuestos al resto del codigo
VARIANT_BINARY = 'binary'
VARIANT_DEVELOPMENT = 'development'

# Longitud minima del nombre base para aceptar el recorte del sufijo
MIN_BASE_LENGTH = 2

_SUFFIX_TYPES = {**{s: VARIANT_BINARY for s in BINARY_SUFFIXES},
                 **{s: VARIANT_DEVELOPMENT for s in DEVELOPMENT_SUFFIXES}}


def split_variant(name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Divide un nombre en (nombre base, tipo de variante).

    Devuelve ``(name, None)`` cuando el nombre no encaja con la heuristica.
    """
    if not name or '-' not in name:
        return name, None

    base, _, suffix = name.rpartition('-')
    variant_type = _SUFFIX_TYPES.get(suffix.lower())

    if variant_type is None or len(base) < MIN_BASE_LENGTH:
        return name, None

    return base, variant_type


def get_base_package_name(name: Optional[str]) -> Optional[str]:
    """Nombre del programa base sin el sufijo de variante."""
    return split_variant(name)[0]


def get_variant_type(name: Optional[str]) -> Optional[str]:
    """Tipo de variante (:data:`VARIANT_BINARY`, :data:`VARIANT_DEVELOPMENT`) o None."""
    return split_variant(name)[1]


def is_variant(name: Optional[str]) -> bool:
    """Indica si el nombre encaja con la heuristica de variante."""
    return get_variant_type(name) is not None


def group_by_base_name(names: Iterable[str]) -> Dict[str, List[str]]:
    """Agrupa una coleccion de nombres por su nombre base.

    Las claves son nombres base y los valores la lista de nombres originales
    ordenada alfabeticamente. Sirve para detectar en un mismo conjunto de
    resultados los grupos ``foo`` / ``foo-bin`` / ``foo-git``.
    """
    groups: Dict[str, List[str]] = {}

    for name in names:
        if name:
            groups.setdefault(get_base_package_name(name), []).append(name)

    for group in groups.values():
        group.sort()

    return groups
