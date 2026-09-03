import json
import logging
import os
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path
from subprocess import Popen
from threading import Lock
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal, QCoreApplication, QSize, QLockFile
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu

from bauh import __app_name__
from bauh.api.abstract.model import PackageUpdate
from bauh.api.http import HttpClient
from bauh.api.paths import TEMP_DIR
from bauh.context import generate_i18n
from bauh.view.core.tray_client import TRAY_CHECK_FILE, TRAY_LOCK_FILE, is_manage_window_running
from bauh.view.core.update import check_for_update
from bauh.view.qt.about import AboutDialog
from bauh.view.qt.qt_utils import load_resource_icon
from bauh.view.util import util, resource
from bauh.view.util.translation import I18n

CLI_NAME = f'{__app_name__}-cli'

# margen para que los hilos terminen su iteracion actual antes de salir
THREAD_STOP_TIMEOUT = 2000

_instance_lock: Optional[QLockFile] = None


def acquire_single_instance_lock(logger: logging.Logger) -> bool:
    """Intenta reservar el bloqueo de bandeja unica. Devuelve False si ya hay otra en marcha."""
    global _instance_lock

    try:
        Path(TEMP_DIR).mkdir(exist_ok=True, parents=True, mode=0o700)
        lock = QLockFile(TRAY_LOCK_FILE)
        lock.setStaleLockTime(0)

        if not lock.tryLock(0):
            logger.warning(f"another tray instance already holds the lock '{TRAY_LOCK_FILE}'")
            return False

        _instance_lock = lock  # la referencia debe sobrevivir a la funcion o el bloqueo se libera
        return True
    except Exception:
        logger.warning(f"could not handle the tray lock file '{TRAY_LOCK_FILE}'", exc_info=True)
        return True  # ante la duda se permite arrancar: el bloqueo es una proteccion, no un requisito


def get_cli_command(logger: logging.Logger) -> Optional[List[str]]:
    """Resuelve el comando de la CLI como lista de argumentos (soporta rutas con espacios)."""
    if os.getenv('APPIMAGE'):
        startup_exec, appdir = os.getenv('APPRUN_STARTUP_EXEC_PATH'), os.getenv('APPDIR')

        if startup_exec and appdir:
            return [startup_exec, f'{appdir}usr/bin/{CLI_NAME}']

        logger.warning('running as an AppImage, but APPRUN_STARTUP_EXEC_PATH/APPDIR are not defined')

    candidates = []

    venv = os.getenv('VIRTUAL_ENV')
    if venv:
        candidates.append(f'{venv}/bin/{CLI_NAME}')

    candidates.append(f'{sys.prefix}/bin/{CLI_NAME}')

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return [path]

        logger.debug(f"'{CLI_NAME}' not executable at '{path}'")

    path_match = shutil.which(CLI_NAME)
    if path_match:
        return [path_match]

    logger.warning(f"'{CLI_NAME}' not found in PATH: falling back to the 'bauh.cli.app' module")
    return [sys.executable, '-m', 'bauh.cli.app']


def list_updates(logger: logging.Logger, timeout: Optional[int] = None) -> List[PackageUpdate]:
    cmd = get_cli_command(logger)

    if not cmd:
        logger.warning(f'"{CLI_NAME}" seems not to be installed')
        return []

    full_cmd = [*cmd, 'updates', '-f', 'json']

    try:
        proc = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning(f'Command "{CLI_NAME} updates" timed out after {timeout} seconds')
        return []
    except OSError:
        logger.warning(f'Command "{CLI_NAME} updates" could not be executed', exc_info=True)
        return []

    output = proc.stdout.decode(errors='replace') if proc.stdout else ''
    error_output = proc.stderr.decode(errors='replace') if proc.stderr else ''

    if proc.returncode != 0:
        log_output = (error_output or output).replace('\n', ' ') or ' '
        logger.warning(f'Command "{CLI_NAME} updates" returned an unexpected exitcode ({proc.returncode}). '
                       f'Output: {log_output}')
        return []

    if error_output:
        logger.debug(f'Command "{CLI_NAME} updates" wrote to stderr: {error_output.strip()}')

    if not output.strip():
        logger.info('No updates found')
        return []

    try:
        parsed = json.loads(output)
    except (json.JSONDecodeError, ValueError):
        logger.warning(f'Command "{CLI_NAME} updates" returned an invalid JSON payload', exc_info=True)
        return []

    try:
        return [PackageUpdate(pkg_id=o['id'], name=o['name'], version=o['version'], pkg_type=o['type'])
                for o in parsed]
    except (KeyError, TypeError):
        logger.warning(f'Command "{CLI_NAME} updates" returned an unexpected JSON structure', exc_info=True)
        return []


class InterruptibleThread(QThread):
    """QThread con un sueno troceado que puede abortarse con requestInterruption()."""

    SLEEP_STEP_MS = 200

    def sleep_interruptible(self, seconds: float) -> bool:
        """Duerme el tiempo indicado. Devuelve False si se ha pedido la interrupcion."""
        remaining = int(max(0.0, seconds) * 1000)

        while remaining > 0:
            if self.isInterruptionRequested():
                return False

            step = min(self.SLEEP_STEP_MS, remaining)
            self.msleep(step)
            remaining -= step

        return not self.isInterruptionRequested()


class UpdateCheck(InterruptibleThread):

    signal = pyqtSignal(list)

    def __init__(self, check_interval: int, lock: Lock, check_file: bool, logger: logging.Logger, parent=None):
        super(UpdateCheck, self).__init__(parent)
        self.check_interval = check_interval
        self.lock = lock
        self.check_file = check_file
        self.logger = logger

    def _notify_updates(self) -> bool:
        with self.lock:
            try:
                # la CLI no puede tardar mas que el propio intervalo: si no, el lock queda tomado
                updates = list_updates(self.logger, timeout=max(60, int(self.check_interval * 60)))
            except Exception:
                # una excepcion no capturada en QThread.run aborta el proceso con PyQt5 >= 5.5
                self.logger.error('Could not check for updates', exc_info=True)
                return True

            if updates is not None:
                self.signal.emit(updates)

        return self.sleep_interruptible(self.check_interval * 60)

    def run(self):
        while not self.isInterruptionRequested():
            if self.check_file:
                if os.path.exists(TRAY_CHECK_FILE):
                    if not self._notify_updates():
                        break

                    try:
                        os.remove(TRAY_CHECK_FILE)
                    except OSError:
                        self.logger.warning(f"Could not remove the tray check file '{TRAY_CHECK_FILE}'",
                                            exc_info=True)
                elif not self.sleep_interruptible(self.check_interval):
                    break
            elif not self._notify_updates():
                break


class AppUpdateCheck(InterruptibleThread):

    def __init__(self, http_client: HttpClient, logger: logging.Logger, i18n: I18n, interval: int = 300):
        super(AppUpdateCheck, self).__init__()
        self.interval = interval
        self.http_client = http_client
        self.logger = logger
        self.i18n = i18n

    def run(self):
        while not self.isInterruptionRequested():
            try:
                update_msg = check_for_update(http_client=self.http_client, logger=self.logger, i18n=self.i18n,
                                              tray=True)
            except Exception:
                self.logger.error('Could not check for a new application version', exc_info=True)
                update_msg = None

            if update_msg:
                util.notify_user(msg=update_msg)

            if not self.sleep_interruptible(self.interval):
                break


class TrayIcon(QSystemTrayIcon):

    def __init__(self, config: dict, screen_size: QSize, logger: logging.Logger, manage_process: Popen = None, settings_process: Popen = None):
        super(TrayIcon, self).__init__()
        self.app_config = config
        self.i18n = generate_i18n(config, resource.get_path('locale/tray'))
        self.screen_size = screen_size
        self.manage_process = manage_process
        self.settings_process = settings_process
        self.logger = logger
        self.http_client = HttpClient(logger=logger)

        if config['ui']['tray']['default_icon']:
            self.icon_default = QIcon(config['ui']['tray']['default_icon'])
        else:
            self.icon_default = QIcon.fromTheme('bauh_tray_default')

        if self.icon_default.isNull():
            self.icon_default = load_resource_icon('img/gekko-bauh.png', 24)

        if config['ui']['tray']['updates_icon']:
            self.icon_updates = QIcon(config['ui']['tray']['updates_icon'])
        else:
            self.icon_updates = QIcon.fromTheme('bauh_tray_updates')

        if self.icon_updates.isNull():
            # variante con insignia para distinguir el estado "hay actualizaciones"
            self.icon_updates = load_resource_icon('img/gekko-bauh-update.png', 24)

        self.setIcon(self.icon_default)

        self.menu = QMenu()

        self.action_manage = self.menu.addAction(self.i18n['tray.action.manage'])
        self.action_manage.triggered.connect(self.show_manage_window)

        self.action_settings = self.menu.addAction(self.i18n['tray.settings'].capitalize())
        self.action_settings.triggered.connect(self.show_settings_window)

        self.action_about = self.menu.addAction(self.i18n['tray.action.about'])
        self.action_about.triggered.connect(self.show_about)

        self.action_exit = self.menu.addAction(self.i18n['tray.action.exit'])
        self.action_exit.triggered.connect(self.quit_application)

        self.setContextMenu(self.menu)

        self.manage_window = None
        self.dialog_about = None
        self.settings_window = None

        self.check_lock = Lock()
        self.check_thread = UpdateCheck(check_interval=int(config['updates']['check_interval']), check_file=False, lock=self.check_lock, logger=logger)
        self.check_thread.signal.connect(self.notify_updates)
        self.check_thread.start()

        self.recheck_thread = UpdateCheck(check_interval=5, check_file=True, lock=self.check_lock, logger=logger)
        self.recheck_thread.signal.connect(self.notify_updates)
        self.recheck_thread.start()

        self.update_thread = AppUpdateCheck(http_client=self.http_client, logger=self.logger, i18n=self.i18n)
        self.update_thread.start()

        self.last_updates = set()
        self.update_notification = bool(config['system']['notifications'])
        self.lock_notify = Lock()

        self.activated.connect(self.handle_click)
        self.set_default_tooltip()

    def set_default_tooltip(self):
        self.setToolTip(f"{self.i18n['tray.action.manage']} ({__app_name__})".lower())

    def handle_click(self, reason):
        if reason == self.Trigger:
            self.show_manage_window()

    def stop_threads(self) -> None:
        """Pide la interrupcion de los hilos de sondeo y los espera antes de salir."""
        threads = (self.check_thread, self.recheck_thread, self.update_thread)

        for thread in threads:
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()

        for thread in threads:
            if thread.isRunning() and not thread.wait(THREAD_STOP_TIMEOUT):
                self.logger.warning(f"The tray thread '{thread.__class__.__name__}' did not stop within "
                                    f'{THREAD_STOP_TIMEOUT} milliseconds')

    def quit_application(self) -> None:
        """Salida ordenada: detiene los hilos propios y deja vivos los procesos hijo ya lanzados."""
        self.stop_threads()
        self.hide()
        QCoreApplication.exit()

    def notify_updates(self, updates: List[PackageUpdate], notify_user: bool = True):
        self.lock_notify.acquire()

        try:
            if len(updates) > 0:
                self.logger.info(f"{len(updates)} updates available")
                update_keys = {f'{up.type}:{up.id}:{up.version}' for up in updates}

                new_icon = self.icon_updates

                if update_keys.difference(self.last_updates):
                    self.last_updates = update_keys
                    n_updates = len(updates)
                    ups_by_type = {}

                    for key in update_keys:
                        ptype = key.split(':')[0]
                        count = ups_by_type.get(ptype)
                        count = 1 if count is None else count + 1
                        ups_by_type[ptype] = count

                    msg = StringIO()
                    msg.write(self.i18n[f"notification.update{'' if n_updates == 1 else 's'}"].format(n_updates))

                    if len(ups_by_type) > 1:
                        for ptype in sorted(ups_by_type):
                            msg.write(f'\n  * {ptype} ({ups_by_type[ptype]})')

                    msg.seek(0)
                    msg = msg.read()
                    self.setToolTip(msg)

                    if self.update_notification and notify_user:
                        util.notify_user(msg=msg)

            else:
                self.last_updates.clear()
                new_icon = self.icon_default
                self.set_default_tooltip()

            if self.icon().cacheKey() != new_icon.cacheKey():  # changes the icon if needed
                self.setIcon(new_icon)

        finally:
            self.lock_notify.release()

    def _new_app_process(self, *extra_args: str) -> Popen:
        # se ejecuta como modulo ('-m bauh.app') para que el paquete se resuelva tambien
        # desde un checkout sin instalar
        return Popen([sys.executable, '-m', 'bauh.app', *extra_args])

    def show_manage_window(self):
        if self.manage_process is not None and self.manage_process.poll() is None:
            return  # ya hay una ventana de gestion viva bajo el control de la bandeja

        if is_manage_window_running():
            # una ventana reiniciada desde los ajustes es huerfana para la bandeja:
            # se detecta por el PID registrado para no abrir una segunda
            self.logger.info('a management window is already running: not opening another one')
            self.manage_process = None
            return

        self.manage_process = self._new_app_process()

    def show_settings_window(self):
        if self.settings_process is not None and self.settings_process.poll() is None:
            return

        self.settings_process = self._new_app_process('--settings')

    def show_about(self):
        if self.dialog_about is None:
            self.dialog_about = AboutDialog(self.app_config)

        if self.dialog_about.isHidden():
            self.dialog_about.show()
