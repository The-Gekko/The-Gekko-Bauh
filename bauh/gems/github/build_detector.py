"""Detección del método de construcción de un repositorio clonado.

IMPORTANTE — qué protege y qué no protege esta lista:

La lista de métodos admitidos NO es una defensa contra código malicioso.  Detectar un
``PKGBUILD`` o un ``Cargo.toml`` sólo dice cómo se construye el proyecto, nunca qué hace su
código: construir cualquier repositorio ejecuta código de terceros (funciones ``build()``
y ``package()`` del PKGBUILD, ``build.rs``, ``setup.py``, hooks de compilación...).

Lo que sí consigue la lista es que la instalación pase siempre por un gestor que el sistema
conoce (``pacman``, ``pipx``, ``cargo``), de modo que lo instalado pueda desinstalarse
después y no se rocíen archivos sueltos por el sistema con un ``sudo make install``.

Por eso el controlador exige una confirmación explícita del usuario, mostrando el
repositorio, el método detectado y el comando literal, antes de construir nada; y por eso
la contraseña de root nunca se le pasa al paso de construcción.
"""

import os
from enum import Enum
from typing import Iterable, List, Optional, Tuple


class BuildMethod(Enum):
    PKGBUILD = 'PKGBUILD'
    MAKEFILE = 'Makefile'
    INSTALL_SCRIPT = 'install.sh'
    PYTHON_SETUP = 'Python (pipx)'
    CARGO = 'Cargo (Rust)'
    MESON = 'Meson'
    CMAKE = 'CMake'
    # identificador estable: la etiqueta visible se resuelve por i18n en el controlador
    UNKNOWN = 'unknown'


# comando de construcción y si hace falta root para el paso de instalación posterior.
#
# - PKGBUILD: 'makepkg' se niega a ejecutarse como root, así que se construye como usuario y
#   después se instala el .pkg.tar.* resultante con 'pacman -U' (ese paso sí necesita root).
# - Python: se usa pipx porque en Arch/Solus el intérprete del sistema está marcado como
#   EXTERNALLY-MANAGED (PEP 668) y 'pip install --user .' falla; nunca se usa
#   '--break-system-packages'.
# - Cargo: 'cargo install' ya compila en modo release en su propio directorio, así que
#   ejecutar antes 'cargo build --release' sólo duplicaba el trabajo.
BUILD_COMMANDS = {
    BuildMethod.PKGBUILD: ('makepkg -s --noconfirm', True),
    BuildMethod.MAKEFILE: (None, False),
    BuildMethod.INSTALL_SCRIPT: (None, False),
    BuildMethod.PYTHON_SETUP: ('pipx install .', False),
    BuildMethod.CARGO: ('cargo install --path . --locked', False),
    BuildMethod.MESON: (None, False),
    BuildMethod.CMAKE: (None, False),
}

# métodos que la gem sabe construir e (sobre todo) desinstalar después
SUPPORTED_METHODS = frozenset({BuildMethod.PKGBUILD, BuildMethod.PYTHON_SETUP,
                               BuildMethod.CARGO})

# herramienta que debe existir en el sistema para cada método admitido
REQUIRED_BINARIES = {
    BuildMethod.PKGBUILD: 'makepkg',
    BuildMethod.PYTHON_SETUP: 'pipx',
    BuildMethod.CARGO: 'cargo',
}

# Orden de detección.  Los métodos admitidos van primero a propósito: un proyecto de Rust o
# de Python con un Makefile de conveniencia debe construirse con cargo o pipx (que dejan el
# software desinstalable) y no quedarse en «instalación manual requerida».
DETECTION_ORDER: Tuple[Tuple[BuildMethod, Tuple[str, ...]], ...] = (
    (BuildMethod.PKGBUILD, ('PKGBUILD',)),
    (BuildMethod.PYTHON_SETUP, ('setup.py', 'pyproject.toml')),
    (BuildMethod.CARGO, ('Cargo.toml',)),
    (BuildMethod.MESON, ('meson.build',)),
    (BuildMethod.CMAKE, ('CMakeLists.txt',)),
    (BuildMethod.MAKEFILE, ('Makefile', 'makefile', 'GNUmakefile')),
    (BuildMethod.INSTALL_SCRIPT, ('install.sh', 'setup.sh')),
)


def detect_build_method(repo_path: str) -> Tuple[BuildMethod, Optional[str]]:
    """Analiza la raíz de un repositorio clonado y devuelve (método, comando o ``None``)."""
    if not repo_path or not os.path.isdir(repo_path):
        return BuildMethod.UNKNOWN, None

    try:
        root_files = set(os.listdir(repo_path))
    except OSError:
        return BuildMethod.UNKNOWN, None

    for method, markers in DETECTION_ORDER:
        if root_files.intersection(markers):
            return method, BUILD_COMMANDS[method][0]

    return BuildMethod.UNKNOWN, None


def requires_root(method: BuildMethod) -> bool:
    """Indica si el método necesita root para el paso de instalación (nunca para construir)."""
    return BUILD_COMMANDS.get(method, (None, False))[1]


def is_supported(method: BuildMethod) -> bool:
    """Indica si la gem sabe construir e instalar con este método."""
    return method in SUPPORTED_METHODS


def get_required_binary(method: BuildMethod) -> Optional[str]:
    """Herramienta necesaria para construir con este método."""
    return REQUIRED_BINARIES.get(method)


def method_from_value(value: Optional[str]) -> BuildMethod:
    """Recupera el método a partir del valor almacenado en el paquete o en el registro."""
    if value:
        for method in BuildMethod:
            if method.value == value:
                return method

    return BuildMethod.UNKNOWN


def uninstall_command(method: BuildMethod,
                      artifacts: Optional[Iterable[str]]) -> Optional[List[str]]:
    """Comando que deshace lo que la construcción instaló fuera del clon.

    ``artifacts`` son los nombres registrados durante la instalación: los paquetes de
    pacman, la aplicación de pipx o el crate de cargo.
    """
    names = [name for name in (artifacts or []) if name]

    if not names:
        return None

    if method == BuildMethod.PKGBUILD:
        return ['pacman', '-R', '--noconfirm', *names]

    if method == BuildMethod.PYTHON_SETUP:
        return ['pipx', 'uninstall', names[0]]

    if method == BuildMethod.CARGO:
        return ['cargo', 'uninstall', names[0]]

    return None


def uninstall_requires_root(method: BuildMethod) -> bool:
    """Sólo la desinstalación vía pacman necesita privilegios de root."""
    return method == BuildMethod.PKGBUILD
