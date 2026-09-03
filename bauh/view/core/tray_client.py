import os
from pathlib import Path
from typing import Optional

from bauh.api.paths import CACHE_DIR, TEMP_DIR

# fichero que indica al icono de bandeja que debe volver a comprobar si hay actualizaciones.
# lleva un nombre propio del fork para no competir con una bandeja del bauh oficial que
# comparta el mismo CACHE_DIR
TRAY_CHECK_FILE = f'{CACHE_DIR}/notify_tray_gekko'

# fichero de bloqueo que garantiza una unica bandeja del fork por usuario
TRAY_LOCK_FILE = f'{TEMP_DIR}/tray.lock'

# fichero con el PID de la ventana de gestion en marcha (evita ventanas duplicadas tras un reinicio)
MANAGE_WINDOW_PID_FILE = f'{TEMP_DIR}/manage_window.pid'


def notify_tray():
    Path(CACHE_DIR).mkdir(exist_ok=True, parents=True)

    with open(TRAY_CHECK_FILE, 'w+') as f:
        f.write('')


def register_manage_window(pid: Optional[int] = None) -> None:
    """Anota el PID de la ventana de gestion para que la bandeja pueda adoptarla tras un reinicio."""
    try:
        Path(TEMP_DIR).mkdir(exist_ok=True, parents=True, mode=0o700)

        with open(MANAGE_WINDOW_PID_FILE, 'w+') as f:
            f.write(str(os.getpid() if pid is None else pid))
    except OSError:
        pass  # es una optimizacion: si no se puede escribir, la bandeja seguira usando su propio handle


def read_manage_window_pid() -> Optional[int]:
    """Devuelve el PID anotado de la ventana de gestion, o None si no hay ninguno valido."""
    try:
        with open(MANAGE_WINDOW_PID_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def is_manage_window_running() -> bool:
    """Indica si el PID anotado corresponde a un proceso vivo."""
    pid = read_manage_window_pid()

    if pid is None or pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # existe, pero pertenece a otro usuario
    except OSError:
        return False

    return True
