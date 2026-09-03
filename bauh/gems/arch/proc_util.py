import multiprocessing
import os
from pwd import getpwnam
from typing import Callable, Optional, TypeVar

R = TypeVar('R')

# Contexto de multiprocessing explicito.
#
# El metodo de arranque por defecto cambia segun la version de Python: 'fork' hasta 3.13 y
# 'forkserver' a partir de 3.14. Estas llamadas se hacen desde hilos de trabajo (Qt, descargas,
# lectura de PKGBUILD), y 'fork' sobre un proceso multihilo emite DeprecationWarning desde 3.12
# y puede dejar al hijo bloqueado con los locks heredados (logging, urllib3).
#
# Se fija 'forkserver' porque arranca el hijo desde un proceso limpio y sin hilos, existe en
# todas las versiones soportadas (3.8-3.14) y da el mismo comportamiento en todas ellas. Exige
# que el objetivo sea serializable con pickle: CallAsUser y WriteToFile son clases de modulo,
# asi que lo son (una lambda o un closure, no).
_MP_START_METHOD = 'forkserver'
_mp_context = multiprocessing.get_context(_MP_START_METHOD)


class CallAsUser:

    def __init__(self, target: Callable[[], R], user: str):
        self._target = target
        self._user = user

    def __call__(self, *args, **kwargs) -> R:
        try:
            os.setuid(getpwnam(self._user).pw_uid)
            return self._target()
        except Exception:
            import logging; logging.error("Exception occurred", exc_info=True)


class WriteToFile:

    def __init__(self, file_path: str, content: str):
        self._file_path = file_path
        self._content = content

    def __call__(self, *args, **kwargs) -> bool:
        try:
            with open(self._file_path, 'w+') as f:
                f.write(self._content)

            return True
        except Exception:
            import logging; logging.error("Exception occurred", exc_info=True)
            return False


def exec_as_user(target: Callable[[], R], user: Optional[str] = None) -> R:
    if user:
        with _mp_context.Pool(1) as pool:
            return pool.apply(CallAsUser(target, user))
    else:
        return target()


def write_as_user(content: str, file_path: str, user: Optional[str] = None) -> bool:
    return exec_as_user(target=WriteToFile(file_path=file_path, content=content),
                        user=user)
