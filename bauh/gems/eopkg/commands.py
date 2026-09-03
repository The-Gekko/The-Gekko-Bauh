"""Constructores de las líneas de comando de ``eopkg``.

Se usan los alias cortos nativos de eopkg (``it``, ``rmf``, ``up``, ``ur``, ``sr``, ``li``,
``la``, ``dc``, ``hs``, ``r-i``).

Dos modificadores aparecen en casi todos los comandos y conviene no confundirlos:

* ``--no-color`` (equivalente a ``-N``) **sólo** suprime las secuencias de color ANSI.
  NO desactiva los prompts interactivos, al contrario de lo que afirmaba el mensaje del
  commit 8baaa445.
* ``-y`` (``--yes-all``) es el modificador realmente no interactivo: responde «yes» a la
  pregunta «Do you want to continue ? (yes/no)».  Por eso lo llevan todos los comandos que
  modifican el sistema.

Regla innegociable del proyecto: la desinstalación se hace SIEMPRE con ``eopkg rmf``, que
elimina el paquete y las dependencias que quedan huérfanas, en orden.  Nunca ``remove``
ni ``rm`` a secas.
"""

from typing import Iterable, List, Optional

BINARY = 'eopkg'
NO_COLOR = '--no-color'
YES_ALL = '-y'


def _build(subcommand: str, args: Optional[Iterable[str]] = None,
           yes: bool = False) -> List[str]:
    cmd = [BINARY, subcommand, NO_COLOR]

    if yes:
        cmd.append(YES_ALL)

    if args:
        cmd.extend(args)

    return cmd


def search_command(words: Iterable[str]) -> List[str]:
    """``eopkg sr --no-color <palabras>``"""
    return _build('sr', words)


def list_installed_command(install_info: bool = False) -> List[str]:
    """``eopkg li --no-color [--install-info]``"""
    return _build('li', ['--install-info'] if install_info else None)


def list_available_command() -> List[str]:
    """``eopkg la --no-color``"""
    return _build('la')


def list_upgrades_command(install_info: bool = False) -> List[str]:
    """``eopkg list-upgrades --no-color [--install-info]`` (este comando no tiene alias corto)"""
    return _build('list-upgrades', ['--install-info'] if install_info else None)


def info_command(names: Iterable[str]) -> List[str]:
    """``eopkg info --no-color <paquetes>``"""
    return _build('info', names)


def install_command(names: Iterable[str]) -> List[str]:
    """``sudo eopkg it --no-color -y <paquetes>``"""
    return _build('it', names, yes=True)


def uninstall_command(names: Iterable[str]) -> List[str]:
    """``sudo eopkg rmf --no-color -y <paquetes>`` (rmf: paquete + huérfanas, en orden)"""
    return _build('rmf', names, yes=True)


def upgrade_command(names: Optional[Iterable[str]] = None) -> List[str]:
    """``sudo eopkg up --no-color -y [paquetes]``: una única transacción para todos."""
    return _build('up', names, yes=True)


def update_repos_command() -> List[str]:
    """``sudo eopkg ur --no-color``"""
    return _build('ur')


def delete_cache_command() -> List[str]:
    """``sudo eopkg dc --no-color``"""
    return _build('dc')


def history_command() -> List[str]:
    """``eopkg hs --no-color``"""
    return _build('hs')


def reinstall_command(names: Iterable[str]) -> List[str]:
    """``sudo eopkg r-i --no-color -y <paquetes>``"""
    return _build('r-i', names, yes=True)
