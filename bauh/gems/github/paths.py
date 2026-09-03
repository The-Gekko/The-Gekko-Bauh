"""Construcción y validación de las rutas locales de los repositorios clonados.

El clon de un repositorio vive en ``<repos_dir>/<owner>/<repo>``: incluir al propietario
evita que dos repositorios homónimos de distintas cuentas colisionen (y que instalar
``owner2/dotfiles`` acabe compilando el código de ``owner1/dotfiles``).

Como la desinstalación borra recursivamente esa ruta, tanto el propietario como el nombre
del repositorio se validan con una expresión regular estricta y la ruta resultante se
comprueba, ya resuelta, contra el directorio raíz configurado.
"""

import os
import re
from typing import Optional

# GitHub admite letras, dígitos, '-', '_' y '.' en propietarios y repositorios
RE_REPO_COMPONENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')

# nombres que nunca pueden formar parte de una ruta derivada de datos remotos
FORBIDDEN_COMPONENTS = frozenset({'.', '..', '.git'})


def is_valid_repo_component(value: Optional[str]) -> bool:
    """Indica si un propietario o nombre de repositorio puede usarse como parte de una ruta."""
    if not value or not isinstance(value, str):
        return False

    if value in FORBIDDEN_COMPONENTS:
        return False

    if '/' in value or '\\' in value or os.sep in value:
        return False

    return bool(RE_REPO_COMPONENT.match(value))


def normalize_repo_name(value: Optional[str]) -> Optional[str]:
    """Quita el sufijo '.git' del nombre de un repositorio."""
    if not value:
        return None

    return value[:-4] if value.endswith('.git') else value


def build_clone_path(repos_dir: str, owner: Optional[str],
                     repo_name: Optional[str]) -> Optional[str]:
    """Devuelve ``<repos_dir>/<owner>/<repo>`` o ``None`` si algún componente no es válido."""
    if not repos_dir:
        return None

    repo_name = normalize_repo_name(repo_name)

    if not is_valid_repo_component(owner) or not is_valid_repo_component(repo_name):
        return None

    return os.path.join(os.path.expanduser(repos_dir), owner, repo_name)


def is_inside(base_dir: str, path: str) -> bool:
    """Indica si ``path``, una vez resuelto, queda estrictamente dentro de ``base_dir``."""
    if not base_dir or not path:
        return False

    base = os.path.realpath(os.path.expanduser(base_dir))
    target = os.path.realpath(os.path.expanduser(path))

    if base == target:
        return False

    try:
        return os.path.commonpath((base, target)) == base
    except ValueError:  # rutas en unidades distintas o mezcla de absoluta y relativa
        return False


def is_safe_clone_path(repos_dir: str, path: Optional[str]) -> bool:
    """Comprueba que una ruta puede borrarse: está dentro de repos_dir y es un clon de git."""
    if not path or not is_inside(repos_dir, path):
        return False

    return os.path.exists(os.path.join(path, '.git'))
