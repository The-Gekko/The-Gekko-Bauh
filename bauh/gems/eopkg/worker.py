"""Tareas de arranque de la gem de eopkg.

La única, por ahora, sincroniza los índices de los repositorios de Solus.  Es imprescindible:
``eopkg list-upgrades`` responde a partir del índice local, así que sin un ``eopkg ur``
previo bauh muestra «no hay actualizaciones» aunque Solus haya publicado paquetes.  La gem
de Arch resuelve lo mismo con ``SyncDatabases`` (``pacman -Syy``) en ``bauh/gems/arch/worker.py``.
"""

import logging
import traceback
from threading import Thread
from typing import Callable, Optional

from bauh.api.abstract.handler import TaskManager
from bauh.commons.boot import CreateConfigFile
from bauh.commons.html import bold
from bauh.commons.system import RE_SUDO_OUTPUT, SimpleProcess
from bauh.gems.eopkg import commands, get_icon_path, index
from bauh.view.util.translation import I18n


class SyncRepositories(Thread):
    """Ejecuta ``sudo eopkg ur`` al arrancar, como mucho una vez por día natural."""

    def __init__(self, taskman: TaskManager, root_password: Optional[str], i18n: I18n,
                 logger: logging.Logger, create_config: CreateConfigFile,
                 extra_env: Optional[dict] = None,
                 on_synchronized: Optional[Callable[[], None]] = None):
        super(SyncRepositories, self).__init__(daemon=True)
        self.taskman = taskman
        self.root_password = root_password
        self.i18n = i18n
        self.logger = logger
        self.create_config = create_config
        self.extra_env = dict(extra_env) if extra_env else None
        self.on_synchronized = on_synchronized
        self.task_id = 'eopkg_repo_sync'
        self.task_name = self.i18n['eopkg.action.update_repos.status']
        self.synchronized = False
        self.taskman.register_task(self.task_id, self.task_name, get_icon_path())

    @staticmethod
    def is_enabled(config: Optional[dict]) -> bool:
        return bool((config or {}).get('sync_repos_startup', True))

    @classmethod
    def should_sync(cls, config: Optional[dict], logger: Optional[logging.Logger] = None) -> bool:
        return cls.is_enabled(config) and index.should_sync(logger)

    def _finish(self, substatus: str):
        self.taskman.update_progress(self.task_id, 100, substatus)
        self.taskman.finish_task(self.task_id)

    def run(self):
        self.taskman.update_progress(
            self.task_id, 0, self.i18n['task.waiting_task'].format(bold(self.create_config.task_name)))
        self.create_config.join()

        config = self.create_config.config

        if not self.is_enabled(config):
            self._finish(self.i18n['eopkg.task.disabled'])
            return

        if not index.should_sync(self.logger):
            # el índice ya se refrescó hoy (por bauh, por el Centro de Software o a mano)
            self.synchronized = True
            self._finish(self.i18n['eopkg.task.synchronized'])
            return

        self.logger.info("Sincronizando los repositorios de eopkg")
        self.taskman.update_progress(self.task_id, 10, None)

        # eopkg no informa de un total con el que calcular un porcentaje real, así que la barra
        # avanza con la salida y se detiene en 90 hasta conocer el código de salida
        progress = 10

        # todo el ciclo de vida del proceso va dentro del mismo try: si la lectura de la
        # salida o la espera fallan (descriptor caído, proceso matado desde fuera), el hilo
        # moriría sin llamar a 'finish_task' y el panel de arranque se quedaría esperando una
        # tarea que ya no existe, sin botón con el que continuar
        try:
            process = SimpleProcess(commands.update_repos_command(),
                                    root_password=self.root_password,
                                    extra_env=self.extra_env)

            for output in process.instance.stdout:
                try:
                    line = output.decode()
                except UnicodeDecodeError:
                    continue

                if line.startswith('[sudo]'):
                    # sudo escribe su petición de contraseña en esta misma salida; se recorta
                    # igual que hace 'ProcessHandler.handle_simple'
                    without_prompt = RE_SUDO_OUTPUT.split(line, maxsplit=1)
                    line = without_prompt[1] if len(without_prompt) > 1 else line

                line = line.strip()

                if line:
                    self.taskman.update_output(self.task_id, line)

                    if progress < 90:
                        progress += 2
                        self.taskman.update_progress(self.task_id, progress, None)

            process.instance.wait()
            returncode = process.instance.returncode
        except Exception:
            self.logger.error("Falló la ejecución de 'eopkg ur'")
            self.logger.error(traceback.format_exc())
            self.synchronized = False
            self._finish(self.i18n['eopkg.task.error'])
            return

        self.synchronized = returncode == 0

        if self.synchronized:
            index.register_sync(self.logger)
            self.logger.info("Repositorios de eopkg sincronizados")

            if self.on_synchronized:
                try:
                    self.on_synchronized()
                except Exception:
                    self.logger.error("Fallo al notificar la sincronización de los repositorios")
                    self.logger.error(traceback.format_exc())

            self._finish(None)
        else:
            # los casos reales son quedarse sin red, dar con un mirror caído o que sudo
            # rechace la contraseña: la sincronización no se registra y list_warnings avisa de
            # que el índice está desfasado, para que «no hay actualizaciones» no se lea como
            # «estás al día».  Cancelar la contraseña del arranque no llega hasta aquí:
            # 'bauh/view/qt/prepare.py' emite 'signal_cancelled' y la aplicación termina sin
            # llegar a llamar a 'prepare()'
            self.logger.warning("No se pudieron sincronizar los repositorios de eopkg "
                                f"(código {returncode})")
            self._finish(self.i18n['eopkg.task.error'])
