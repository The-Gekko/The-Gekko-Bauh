import os
import shutil
import subprocess
import traceback
from typing import Dict, Generator, List, Optional, Set, Tuple, Type

from bauh.api.abstract.context import ApplicationContext
from bauh.api.abstract.controller import (
    SearchResult,
    SettingsController,
    SettingsView,
    SoftwareAction,
    SoftwareManager,
    TransactionResult,
    UpgradeRequirements,
)
from bauh.api.abstract.disk import DiskCacheLoader
from bauh.api.abstract.handler import ProcessWatcher, TaskManager
from bauh.api.abstract.model import (
    CustomSoftwareAction,
    PackageHistory,
    PackageUpdate,
    SoftwarePackage,
)
from bauh.api.abstract.view import (
    FormComponent,
    MessageType,
    PanelComponent,
    TextInputComponent,
)
from bauh.commons.html import bold
from bauh.commons.system import ProcessHandler, SimpleProcess
from bauh.gems.eopkg import EOPKG_CACHE_DIR, commands, get_icon_path, parsers
from bauh.gems.eopkg.config import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SEARCH_LIMIT,
    EopkgConfigManager,
)
from bauh.gems.eopkg.model import EopkgPackage

# la salida de eopkg está traducida al idioma del sistema: se fuerza la locale C (manteniendo
# UTF-8 para no romper la descodificación de los resúmenes) para poder analizarla
EOPKG_ENV = {'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'LANGUAGE': 'C'}

# a partir de este número de paquetes actualizables se deja de consultar 'eopkg info' para
# resolver la versión disponible: la línea de comandos resultante sería desmesurada
MAX_INFO_BATCH = 60


class EopkgManager(SoftwareManager, SettingsController):

    def __init__(self, context: ApplicationContext):
        super(EopkgManager, self).__init__(context=context)
        self.i18n = context.i18n
        self.logger = context.logger
        self.enabled = True
        self.configman = EopkgConfigManager()
        # caché del conjunto de instalados durante la sesión: se invalida tras cada
        # transacción (instalar / desinstalar / actualizar)
        self._installed_index: Optional[Dict[str, dict]] = None
        self._upgradable_names: Optional[List[str]] = None
        self._action_update_repos: Optional[CustomSoftwareAction] = None
        self._action_clean_cache: Optional[CustomSoftwareAction] = None

    # ------------------------------------------------------------------ utilidades

    def _get_config(self) -> dict:
        try:
            return self.configman.get_config()
        except Exception:
            self.logger.error("No se pudo leer la configuración de eopkg")
            self.logger.error(traceback.format_exc())
            return self.configman.get_default_config()

    def _get_timeout(self) -> int:
        timeout = self._get_config().get('command_timeout', DEFAULT_COMMAND_TIMEOUT)

        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            return DEFAULT_COMMAND_TIMEOUT

        return timeout if timeout > 0 else DEFAULT_COMMAND_TIMEOUT

    def _get_search_limit(self) -> int:
        limit = self._get_config().get('search_limit', DEFAULT_SEARCH_LIMIT)

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return DEFAULT_SEARCH_LIMIT

        return limit if limit > 0 else DEFAULT_SEARCH_LIMIT

    def _execute_eopkg(self, cmd: List[str]) -> Tuple[bool, str]:
        """Ejecuta un comando de sólo lectura de eopkg y devuelve (éxito, salida).

        El stderr se registra en el log de la aplicación en lugar de descartarse y el
        proceso lleva un tiempo máximo para que un eopkg bloqueado no cuelgue la interfaz.
        """
        env = dict(os.environ)
        env.update(EOPKG_ENV)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                    timeout=self._get_timeout(), check=False)
        except subprocess.TimeoutExpired:
            self.logger.warning(f"El comando '{' '.join(cmd)}' superó el tiempo máximo de espera")
            return False, ''
        except Exception:
            self.logger.error(f"No se pudo ejecutar el comando '{' '.join(cmd)}'")
            self.logger.error(traceback.format_exc())
            return False, ''

        stderr = parsers.strip_ansi(result.stderr).strip()

        if result.returncode != 0:
            self.logger.warning(f"'{' '.join(cmd)}' terminó con código {result.returncode}"
                                f"{': ' + stderr if stderr else ''}")
        elif stderr:
            self.logger.info(f"'{' '.join(cmd)}' escribió en stderr: {stderr}")

        return result.returncode == 0, parsers.strip_ansi(result.stdout)

    def _new_root_process(self, cmd: List[str], root_password: Optional[str]) -> SimpleProcess:
        return SimpleProcess(cmd, root_password=root_password, extra_env=dict(EOPKG_ENV))

    def _invalidate_installed_cache(self):
        self._installed_index = None
        self._upgradable_names = None

    # ------------------------------------------------------------------ lecturas

    def _read_installed_index(self, refresh: bool = False) -> Dict[str, dict]:
        """Devuelve un índice ``nombre -> {version, release, summary}`` de lo instalado.

        El resultado se cachea durante la sesión porque ``eopkg li`` recorre miles de
        paquetes y la búsqueda lo necesitaba en cada pulsación.
        """
        if self._installed_index is not None and not refresh:
            return self._installed_index

        index: Dict[str, dict] = {}

        # 'li' clásico: aporta el resumen de cada paquete
        success, output = self._execute_eopkg(commands.list_installed_command())

        if success:
            for entry in parsers.parse_package_list(output):
                index[entry['name']] = dict(entry)

        # 'li --install-info': aporta versión y release
        success, output = self._execute_eopkg(commands.list_installed_command(install_info=True))

        if success:
            for entry in parsers.parse_package_list(output):
                current = index.setdefault(entry['name'], dict(entry))

                if entry.get('version'):
                    current['version'] = entry['version']
                    current['release'] = entry.get('release')

        self._installed_index = index
        return index

    def _read_upgradable(self, refresh: bool = False) -> List[str]:
        """Nombres de los paquetes con actualización, cacheados durante la sesión."""
        if self._upgradable_names is not None and not refresh:
            return self._upgradable_names

        success, output = self._execute_eopkg(commands.list_upgrades_command())

        if not success:
            return []

        self._upgradable_names = parsers.parse_upgradable(output)
        return self._upgradable_names

    def _read_info_index(self, names: List[str]) -> Dict[str, Dict[str, dict]]:
        """Consulta ``eopkg info`` para varios paquetes en una sola llamada."""
        if not names:
            return {}

        success, output = self._execute_eopkg(commands.info_command(names))

        if not success:
            return {}

        return parsers.index_info_blocks(parsers.parse_info_blocks(output))

    @staticmethod
    def _version_of(block: Optional[dict]) -> Optional[str]:
        if not block:
            return None

        return parsers.format_version(block.get('version'), block.get('release'))

    # ------------------------------------------------------------------ contrato

    def search(self, words: str, disk_loader: Optional[DiskCacheLoader] = None,
               limit: int = -1, is_url: bool = False) -> SearchResult:
        if is_url:
            return SearchResult.empty()

        self.logger.info(f"eopkg: buscando '{words}'")

        success, output = self._execute_eopkg(commands.search_command(words.split()))

        if not success:
            return SearchResult.empty()

        max_results = limit if limit > 0 else self._get_search_limit()
        installed_index = self._read_installed_index()
        upgradable = set(self._read_upgradable())

        installed, new = [], []

        for entry in parsers.parse_search(output)[0:max_results]:
            name = entry['name']
            installed_data = installed_index.get(name)

            if installed_data is not None:
                pkg = EopkgPackage(name=name,
                                   description=entry.get('summary') or installed_data.get('summary'),
                                   version=parsers.format_version(installed_data.get('version'),
                                                                  installed_data.get('release')),
                                   installed=True,
                                   update=name in upgradable)
                installed.append(pkg)
            else:
                new.append(EopkgPackage(name=name, description=entry.get('summary')))

        return SearchResult(installed=installed, new=new, total=len(installed) + len(new))

    def read_installed(self, disk_loader: Optional[DiskCacheLoader] = None, limit: int = -1,
                       only_apps: bool = False, pkg_types: Optional[Set[Type[SoftwarePackage]]] = None,
                       internet_available: bool = True) -> SearchResult:
        index = self._read_installed_index(refresh=True)
        upgradable = self._read_upgradable(refresh=True) if internet_available else []
        upgradable_set = set(upgradable)

        # la versión disponible sólo se consulta para los paquetes que tienen actualización
        latest_versions: Dict[str, str] = {}

        if upgradable and len(upgradable) <= MAX_INFO_BATCH:
            info_index = self._read_info_index(upgradable)

            for name, sections in info_index.items():
                latest = self._version_of(sections.get('repository'))

                if latest:
                    latest_versions[name] = latest

        installed = []

        for name, data in index.items():
            version = parsers.format_version(data.get('version'), data.get('release'))
            installed.append(EopkgPackage(name=name,
                                          description=data.get('summary'),
                                          version=version,
                                          latest_version=latest_versions.get(name, version),
                                          installed=True,
                                          update=name in upgradable_set))

        return SearchResult(installed=installed, new=None, total=len(installed))

    def install(self, pkg: EopkgPackage, root_password: Optional[str],
                disk_loader: Optional[DiskCacheLoader], watcher: ProcessWatcher) -> TransactionResult:
        handler = ProcessHandler(watcher)
        watcher.change_substatus(self.i18n['eopkg.installing'].format(bold(pkg.name)))

        def handle_output(line: str):
            progress = parsers.parse_install_progress(line)

            if progress:
                current, total = progress

                if total > 0:
                    watcher.change_progress(int((current / total) * 100))

            installing = parsers.parse_installing_package(line)

            if installing:
                watcher.change_substatus(self.i18n['eopkg.installing'].format(bold(installing['name'])))

        success, output = handler.handle_simple(
            self._new_root_process(commands.install_command([pkg.name]), root_password),
            output_handler=handle_output)

        self._invalidate_installed_cache()

        if not success:
            watcher.show_message(title=self.i18n['error'],
                                 body=self.i18n['eopkg.install_error'].format(bold(pkg.name)),
                                 type_=MessageType.ERROR)
            return TransactionResult.fail()

        pkg.installed = True
        pkg.update = False

        installed = [pkg]
        index = self._read_installed_index(refresh=True)

        # eopkg instala también las dependencias: se reportan para que la vista las conozca
        for name in parsers.parse_installed_packages(output):
            if name == pkg.name:
                continue

            data = index.get(name, {})
            installed.append(EopkgPackage(name=name,
                                          description=data.get('summary'),
                                          version=parsers.format_version(data.get('version'),
                                                                         data.get('release')),
                                          installed=True))

        return TransactionResult(success=True, installed=installed, removed=[])

    def uninstall(self, pkg: EopkgPackage, root_password: Optional[str],
                  watcher: ProcessWatcher, disk_loader: Optional[DiskCacheLoader] = None) -> TransactionResult:
        handler = ProcessHandler(watcher)
        watcher.change_substatus(self.i18n['eopkg.removing'].format(bold(pkg.name)))

        # 'rmf' arrastra las dependencias que quedan huérfanas: eopkg las lista antes de
        # actuar y esa lista se enseña al usuario a través del ProcessWatcher
        collector = parsers.TransactionTargetsCollector()
        reported = []

        def handle_output(line: str):
            if collector.feed(line) and not reported:
                reported.append(True)
                announced = ', '.join(collector.targets)
                watcher.print(self.i18n['eopkg.removal_list'].format(announced))
                watcher.change_substatus(self.i18n['eopkg.removal_list'].format(bold(announced)))

        success, output = handler.handle_simple(
            self._new_root_process(commands.uninstall_command([pkg.name]), root_password),
            output_handler=handle_output)

        self._invalidate_installed_cache()

        if collector.targets and not reported:
            watcher.print(self.i18n['eopkg.removal_list'].format(', '.join(collector.targets)))

        if not success:
            watcher.show_message(title=self.i18n['error'],
                                 body=self.i18n['eopkg.remove_error'].format(bold(pkg.name)),
                                 type_=MessageType.ERROR)
            return TransactionResult.fail()

        removed_names = parsers.parse_removed_packages(output) or collector.targets or [pkg.name]

        pkg.installed = False
        pkg.update = False
        removed = [pkg]

        for name in removed_names:
            if name != pkg.name:
                removed.append(EopkgPackage(name=name, installed=False))

        return TransactionResult(success=True, installed=[], removed=removed)

    def downgrade(self, pkg: SoftwarePackage, root_password: Optional[str],
                  handler: ProcessWatcher) -> bool:
        return False

    def upgrade(self, requirements: UpgradeRequirements, root_password: Optional[str],
                watcher: ProcessWatcher) -> bool:
        handler = ProcessHandler(watcher)

        names = [req.pkg.name for req in (requirements.to_upgrade or [])
                 if isinstance(req.pkg, EopkgPackage)]

        if not names:
            return False

        if self._get_config().get('sync_repos_before_upgrade', True):
            watcher.change_substatus(self.i18n['eopkg.action.update_repos.status'])
            synced, _ = handler.handle_simple(
                self._new_root_process(commands.update_repos_command(), root_password))

            if not synced:
                self.logger.warning("No se pudieron actualizar los repositorios de eopkg antes "
                                    "de la actualización")

        watcher.change_substatus(self.i18n['eopkg.upgrading_many'].format(bold(str(len(names)))))

        # una única transacción para todos los paquetes: eopkg resuelve el orden y las
        # dependencias mucho mejor que N invocaciones independientes con sudo
        success, _ = handler.handle_simple(
            self._new_root_process(commands.upgrade_command(names), root_password))

        self._invalidate_installed_cache()
        return success

    def get_managed_types(self) -> Set[Type[SoftwarePackage]]:
        return {EopkgPackage}

    def get_info(self, pkg: EopkgPackage) -> dict:
        info = {self.i18n['eopkg.info.name']: pkg.name}

        success, output = self._execute_eopkg(commands.info_command([pkg.name]))

        if not success:
            info[self.i18n['eopkg.info.summary']] = pkg.description or '-'
            return info

        sections = parsers.index_info_blocks(parsers.parse_info_blocks(output)).get(pkg.name, {})
        block = sections.get('installed') or sections.get('repository') or {}
        repository = sections.get('repository') or {}

        version = parsers.format_version(block.get('version'), block.get('release'))
        latest = parsers.format_version(repository.get('version'), repository.get('release'))

        fields = (('version', version or pkg.version),
                  ('latest_version', latest),
                  ('summary', block.get('summary') or pkg.description),
                  ('description', block.get('description')),
                  ('licenses', block.get('licenses')),
                  ('component', block.get('component')),
                  ('dependencies', block.get('dependencies')),
                  ('installed_size', block.get('installed_size')),
                  ('distribution', block.get('distribution')))

        for key, value in fields:
            if value:
                info[self.i18n[f'eopkg.info.{key}']] = value

        return info

    def get_history(self, pkg: SoftwarePackage) -> PackageHistory:
        return PackageHistory(pkg=pkg, history=[], pkg_status_idx=-1)

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def can_work(self) -> Tuple[bool, Optional[str]]:
        if not shutil.which('eopkg'):
            return False, self.i18n['eopkg.requires_eopkg']

        return True, None

    def requires_root(self, action: SoftwareAction, pkg: Optional[SoftwarePackage] = None) -> bool:
        # instalar, desinstalar y actualizar con eopkg exige siempre privilegios de root
        return action in (SoftwareAction.INSTALL, SoftwareAction.UNINSTALL,
                          SoftwareAction.UPGRADE)

    def prepare(self, task_manager: Optional[TaskManager], root_password: Optional[str],
                internet_available: Optional[bool]):
        pass

    def list_updates(self, internet_available: bool) -> List[PackageUpdate]:
        if not internet_available:
            return []

        names = self._read_upgradable(refresh=True)

        if not names:
            return []

        versions: Dict[str, str] = {}

        if len(names) <= MAX_INFO_BATCH:
            for name, sections in self._read_info_index(names).items():
                latest = self._version_of(sections.get('repository'))

                if latest:
                    versions[name] = latest

        return [PackageUpdate(pkg_id=name, version=versions.get(name, ''), pkg_type='eopkg',
                              name=name)
                for name in names]

    def list_warnings(self, internet_available: bool) -> Optional[List[str]]:
        return None

    def is_default_enabled(self) -> bool:
        return True

    def launch(self, pkg: SoftwarePackage):
        pass

    def get_screenshots(self, pkg: SoftwarePackage) -> Generator[str, None, None]:
        yield from ()

    def clear_data(self, logs: bool = True):
        if os.path.exists(EOPKG_CACHE_DIR):
            try:
                shutil.rmtree(EOPKG_CACHE_DIR)

                if logs:
                    self.logger.info(f"Directorio de caché eliminado: {EOPKG_CACHE_DIR}")
            except Exception:
                if logs:
                    self.logger.error(f"No se pudo eliminar el directorio {EOPKG_CACHE_DIR}")
                    self.logger.error(traceback.format_exc())

    # ------------------------------------------------------------------ ajustes

    def get_settings(self) -> Optional[Generator[SettingsView, None, None]]:
        config = self._get_config()

        fields = [
            TextInputComponent(label=self.i18n['eopkg.config.search_limit'],
                               tooltip=self.i18n['eopkg.config.search_limit.tip'],
                               value=str(config.get('search_limit', DEFAULT_SEARCH_LIMIT)),
                               only_int=True,
                               id_='search_limit'),
            TextInputComponent(label=self.i18n['eopkg.config.command_timeout'],
                               tooltip=self.i18n['eopkg.config.command_timeout.tip'],
                               value=str(config.get('command_timeout', DEFAULT_COMMAND_TIMEOUT)),
                               only_int=True,
                               id_='command_timeout'),
        ]

        yield SettingsView(self, PanelComponent([FormComponent(fields, self.i18n['eopkg.config'])]),
                           icon_path=get_icon_path())

    def save_settings(self, component: PanelComponent) -> Tuple[bool, Optional[List[str]]]:
        config = self._get_config()
        form = component.get_component_by_idx(0, FormComponent)

        for key, default in (('search_limit', DEFAULT_SEARCH_LIMIT),
                             ('command_timeout', DEFAULT_COMMAND_TIMEOUT)):
            raw = form.get_component(key, TextInputComponent).get_value()

            try:
                value = int(raw)
            except (TypeError, ValueError):
                value = default

            config[key] = value if value > 0 else default

        try:
            self.configman.save_config(config)
            return True, None
        except Exception:
            return False, [traceback.format_exc()]

    # ------------------------------------------------------------------ acciones

    def gen_custom_actions(self) -> Generator[CustomSoftwareAction, None, None]:
        yield self.action_update_repos
        yield self.action_clean_cache

    @property
    def action_update_repos(self) -> CustomSoftwareAction:
        if self._action_update_repos is None:
            self._action_update_repos = CustomSoftwareAction(
                i18n_label_key='eopkg.action.update_repos',
                i18n_status_key='eopkg.action.update_repos.status',
                i18n_description_key='eopkg.action.update_repos.description',
                icon_path=get_icon_path(),
                manager=self,
                manager_method='update_repositories',
                requires_internet=True,
                requires_root=True)

        return self._action_update_repos

    @property
    def action_clean_cache(self) -> CustomSoftwareAction:
        if self._action_clean_cache is None:
            self._action_clean_cache = CustomSoftwareAction(
                i18n_label_key='eopkg.action.clean_cache',
                i18n_status_key='eopkg.action.clean_cache.status',
                i18n_description_key='eopkg.action.clean_cache.description',
                icon_path=get_icon_path(),
                manager=self,
                manager_method='clean_download_cache',
                requires_internet=False,
                requires_root=True)

        return self._action_clean_cache

    def update_repositories(self, root_password: Optional[str], watcher: ProcessWatcher) -> bool:
        """Acción "Actualizar repositorios": ``sudo eopkg ur``."""
        handler = ProcessHandler(watcher)
        success, _ = handler.handle_simple(
            self._new_root_process(commands.update_repos_command(), root_password))
        self._invalidate_installed_cache()
        return success

    def clean_download_cache(self, root_password: Optional[str], watcher: ProcessWatcher) -> bool:
        """Acción "Limpiar caché de descargas": ``sudo eopkg dc``."""
        handler = ProcessHandler(watcher)
        success, _ = handler.handle_simple(
            self._new_root_process(commands.delete_cache_command(), root_password))
        return success
