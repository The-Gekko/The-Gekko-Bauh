import glob
import os
import shlex
import shutil
import subprocess
import time
import traceback
from pathlib import Path
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
from bauh.api.abstract.model import PackageHistory, PackageUpdate, SoftwarePackage
from bauh.api.abstract.view import (
    FileChooserComponent,
    FormComponent,
    MessageType,
    PanelComponent,
    SingleSelectComponent,
    TextInputComponent,
)
from bauh.commons.html import bold
from bauh.commons.system import ProcessHandler, SimpleProcess
from bauh.commons.view_utils import new_select
from bauh.gems.github import (
    DEFAULT_REPOS_DIR,
    GITHUB_CACHE_DIR,
    LEGACY_REPOS_DIR,
    get_icon_path,
    gitrepo,
    paths,
    registry,
)
from bauh.gems.github.build_detector import (
    BuildMethod,
    detect_build_method,
    get_required_binary,
    is_supported,
    method_from_value,
    uninstall_command,
    uninstall_requires_root,
)
from bauh.gems.github.build_detector import requires_root as build_requires_root
from bauh.gems.github.config import (
    DEFAULT_CACHE_EXPIRATION,
    DEFAULT_SEARCH_LIMIT,
    GitHubConfigManager,
)
from bauh.gems.github.model import GitHubPackage

API_BASE = 'https://api.github.com'

# prefijo explícito para forzar una búsqueda en la API aunque 'search_enabled' esté a False
SEARCH_PREFIX = 'gh:'

GIT_TIMEOUT = 60


class GitHubManager(SoftwareManager, SettingsController):

    def __init__(self, context: ApplicationContext):
        super(GitHubManager, self).__init__(context=context)
        self.i18n = context.i18n
        self.http_client = context.http_client
        self.logger = context.logger
        self.enabled = True
        self.configman = GitHubConfigManager()
        self.registry = registry.InstallationRegistry(logger=context.logger)
        # caché en memoria de las respuestas de la API: url -> (instante, datos)
        self._api_cache: Dict[str, Tuple[float, object]] = {}
        # clave i18n de la última advertencia de la API (límite de peticiones, token, ...)
        self._api_warning: Optional[str] = None

    # ------------------------------------------------------------------ configuración

    def _get_config(self) -> dict:
        try:
            return self.configman.get_config()
        except Exception:
            self.logger.error("No se pudo leer la configuración de la gem GitHub")
            self.logger.error(traceback.format_exc())
            return self.configman.get_default_config()

    def _get_repos_dir(self) -> str:
        repos_dir = self._get_config().get('repos_dir') or DEFAULT_REPOS_DIR
        return os.path.expanduser(str(repos_dir))

    def _is_clone_only(self) -> bool:
        return bool(self._get_config().get('clone_only', True))

    def _get_int_config(self, key: str, default: int) -> int:
        try:
            value = int(self._get_config().get(key, default))
        except (TypeError, ValueError):
            return default

        return value if value > 0 else default

    # ------------------------------------------------------------------ API de GitHub

    def _api_headers(self) -> dict:
        headers = {'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28'}

        token = self._get_config().get('github_token')

        if token:
            headers['Authorization'] = f'Bearer {str(token).strip()}'

        return headers

    def _cache_key(self, url: str, params: Optional[dict]) -> str:
        if not params:
            return url

        return f"{url}?{'&'.join(f'{k}={v}' for k, v in sorted(params.items()))}"

    def _get_json(self, url: str, params: Optional[dict] = None):
        """Llama a la API de GitHub con caché en memoria y advertencias en lugar de silencio."""
        key = self._cache_key(url, params)
        cached = self._api_cache.get(key)
        expiration = self._get_int_config('cache_expiration', DEFAULT_CACHE_EXPIRATION)

        if cached and (time.time() - cached[0]) < expiration:
            return cached[1]

        try:
            resp = self.http_client.get(url, params=params, headers=self._api_headers(),
                                        single_call=True)
        except Exception:
            self.logger.error(f"Falló la petición a la API de GitHub: {url}")
            self.logger.error(traceback.format_exc())
            self._api_warning = 'github.warning.unreachable'
            return None

        if resp is None:
            self._api_warning = 'github.warning.unreachable'
            return None

        if resp.status_code == 200:
            self._api_warning = None

            try:
                data = resp.json()
            except Exception:
                self.logger.error(f"Respuesta no interpretable de la API de GitHub: {url}")
                return None

            self._api_cache[key] = (time.time(), data)
            return data

        if resp.status_code == 404:
            return None

        if resp.status_code in (403, 429):
            self._api_warning = 'github.warning.rate_limited'
        elif resp.status_code == 401:
            self._api_warning = 'github.warning.bad_token'
        else:
            self._api_warning = 'github.warning.api_error'

        self.logger.warning(f"La API de GitHub respondió {resp.status_code} para {url}")
        return None

    def _fetch_repo_info(self, owner: str, repo_name: str) -> Optional[dict]:
        if not paths.is_valid_repo_component(owner) or \
                not paths.is_valid_repo_component(repo_name):
            return None

        data = self._get_json(f'{API_BASE}/repos/{owner}/{repo_name}')
        return data if isinstance(data, dict) else None

    def _search_github_api(self, query: str, limit: int) -> List[dict]:
        data = self._get_json(f'{API_BASE}/search/repositories',
                              params={'q': query, 'sort': 'stars', 'order': 'desc',
                                      'per_page': limit})

        if not isinstance(data, dict):
            return []

        items = data.get('items')
        return items if isinstance(items, list) else []

    # ------------------------------------------------------------------ conversiones

    def _api_to_package(self, api_data: dict) -> Optional[GitHubPackage]:
        owner = (api_data.get('owner') or {}).get('login') or ''
        repo_name = api_data.get('name') or ''

        if not paths.is_valid_repo_component(owner) or \
                not paths.is_valid_repo_component(repo_name):
            self.logger.warning(f"Se descarta el repositorio '{owner}/{repo_name}': "
                                f"el nombre no es válido como ruta local")
            return None

        clone_path = paths.build_clone_path(self._get_repos_dir(), owner, repo_name)
        is_cloned = bool(clone_path) and os.path.isdir(clone_path)
        branch = api_data.get('default_branch') or 'main'
        license_data = api_data.get('license') or {}

        pkg = GitHubPackage(
            name=repo_name,
            description=api_data.get('description') or self.i18n['github.no_description'],
            version=branch,
            repo_url=api_data.get('html_url') or f'https://github.com/{owner}/{repo_name}',
            owner=owner,
            repo_name=repo_name,
            stars=api_data.get('stargazers_count') or 0,
            clone_path=clone_path,
            cloned=is_cloned,
            installed=is_cloned,
            license=license_data.get('spdx_id'),
            default_branch=branch,
            language=api_data.get('language'),
        )

        if is_cloned:
            self._fill_local_data(pkg, clone_path)

        return pkg

    def _fill_local_data(self, pkg: GitHubPackage, clone_path: str):
        method, _ = detect_build_method(clone_path)
        record = self.registry.get(registry.InstallationRegistry.key_for(pkg.owner,
                                                                        pkg.repo_name)) or {}
        pkg.build_method = record.get('build_method') or method.value
        pkg.installed_artifacts = record.get('artifacts') or []
        pkg.built = bool(pkg.installed_artifacts)
        pkg.version = gitrepo.read_current_branch(clone_path) or pkg.version

    # ------------------------------------------------------------------ contrato

    def search(self, words: str, disk_loader: Optional[DiskCacheLoader] = None,
               limit: int = -1, is_url: bool = False) -> SearchResult:
        query = (words or '').strip()
        forced = query.lower().startswith(SEARCH_PREFIX)

        if forced:
            query = query[len(SEARCH_PREFIX):].strip()

        if not query:
            return SearchResult.empty()

        parsed = gitrepo.parse_github_url(query)

        if parsed:
            api_data = self._fetch_repo_info(*parsed)
            pkg = self._api_to_package(api_data) if api_data else None

            if not pkg:
                return SearchResult.empty()

            return SearchResult(installed=[pkg] if pkg.installed else [],
                                new=[] if pkg.installed else [pkg],
                                total=1)

        if not forced and not self._get_config().get('search_enabled', False):
            # sin esto cada pulsación en la barra de búsqueda golpearía la API pública
            return SearchResult.empty()

        max_results = limit if limit > 0 else self._get_int_config('search_limit',
                                                                  DEFAULT_SEARCH_LIMIT)
        installed, new = [], []

        for item in self._search_github_api(query, max_results):
            pkg = self._api_to_package(item)

            if not pkg:
                continue

            (installed if pkg.installed else new).append(pkg)

        return SearchResult(installed=installed, new=new, total=len(installed) + len(new))

    def _iter_clone_dirs(self, repos_dir: str) -> Generator[str, None, None]:
        """Recorre ``<repos_dir>/<owner>/<repo>`` y también el formato plano heredado."""
        if not os.path.isdir(repos_dir):
            return

        try:
            first_level = sorted(os.scandir(repos_dir), key=lambda e: e.name)
        except OSError:
            return

        for entry in first_level:
            if not entry.is_dir() or entry.name.startswith('.'):
                continue

            if os.path.exists(os.path.join(entry.path, '.git')):
                # formato plano de versiones anteriores: <repos_dir>/<repo>
                yield entry.path
                continue

            try:
                second_level = sorted(os.scandir(entry.path), key=lambda e: e.name)
            except OSError:
                continue

            for sub in second_level:
                if sub.is_dir() and not sub.name.startswith('.') and \
                        os.path.exists(os.path.join(sub.path, '.git')):
                    yield sub.path

    def read_installed(self, disk_loader: Optional[DiskCacheLoader] = None, limit: int = -1,
                       only_apps: bool = False, pkg_types: Optional[Set[Type[SoftwarePackage]]] = None,
                       internet_available: bool = True) -> SearchResult:
        repos_dir = self._get_repos_dir()
        check_updates = bool(self._get_config().get('check_updates', True))
        installed = []

        for clone_path in self._iter_clone_dirs(repos_dir):
            repo_url = gitrepo.read_remote_url(clone_path)
            parsed = gitrepo.parse_github_url(repo_url) if repo_url else None

            if parsed:
                owner, repo_name = parsed
            else:
                owner, repo_name = os.path.basename(os.path.dirname(clone_path)), \
                    os.path.basename(clone_path)

            pkg = GitHubPackage(
                name=repo_name,
                description=self.i18n['github.cloned_repository'].format(f'{owner}/{repo_name}'),
                version=gitrepo.read_current_branch(clone_path) or 'HEAD',
                repo_url=repo_url or f'https://github.com/{owner}/{repo_name}',
                owner=owner,
                repo_name=repo_name,
                clone_path=clone_path,
                cloned=True,
                installed=True,
            )
            self._fill_local_data(pkg, clone_path)

            # 'git rev-list' es local y barato; el 'git fetch' se hace en list_updates
            if check_updates and self._count_commits_behind(clone_path) > 0:
                pkg.update = True

            installed.append(pkg)

        return SearchResult(installed=installed, new=None, total=len(installed))

    # ------------------------------------------------------------------ git

    def _run_git(self, args: List[str], cwd: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True,
                                    timeout=GIT_TIMEOUT, check=False)
        except Exception:
            self.logger.warning(f"No se pudo ejecutar 'git {' '.join(args)}' en {cwd}")
            return False, ''

        return result.returncode == 0, result.stdout.strip()

    def _count_commits_behind(self, clone_path: str) -> int:
        """Commits que el remoto lleva de ventaja según las referencias ya descargadas."""
        success, output = self._run_git(['rev-list', 'HEAD..@{u}', '--count'], clone_path)

        if not success or not output.isdigit():
            return 0

        return int(output)

    # ------------------------------------------------------------------ instalación

    def _method_label(self, method: BuildMethod) -> str:
        if method == BuildMethod.UNKNOWN:
            return self.i18n['github.build_method.unknown']

        return method.value

    @staticmethod
    def _clone_url(pkg: GitHubPackage) -> Optional[str]:
        """URL de clonado derivada del propietario y el repositorio ya validados.

        No se usa directamente la URL que devuelve la API para que 'git clone' nunca reciba
        como argumento una cadena arbitraria (por ejemplo una que empiece por '-').
        """
        if paths.is_valid_repo_component(pkg.owner) and \
                paths.is_valid_repo_component(pkg.repo_name):
            return f'https://github.com/{pkg.owner}/{pkg.repo_name}.git'

        return None

    def _resolve_clone_path(self, pkg: GitHubPackage) -> Optional[str]:
        repos_dir = self._get_repos_dir()
        clone_path = paths.build_clone_path(repos_dir, pkg.owner, pkg.repo_name or pkg.name)

        if clone_path and paths.is_inside(repos_dir, clone_path):
            return clone_path

        return None

    def install(self, pkg: GitHubPackage, root_password: Optional[str],
                disk_loader: Optional[DiskCacheLoader], watcher: ProcessWatcher) -> TransactionResult:
        handler = ProcessHandler(watcher)
        clone_path = self._resolve_clone_path(pkg)

        if not clone_path:
            watcher.show_message(title=self.i18n['error'],
                                 body=self.i18n['github.invalid_repo'].format(
                                     bold(f'{pkg.owner}/{pkg.repo_name}')),
                                 type_=MessageType.ERROR)
            return TransactionResult.fail()

        pkg.clone_path = clone_path

        if not self._clone_or_update(pkg, clone_path, handler, watcher):
            return TransactionResult.fail()

        pkg.cloned = True
        pkg.installed = True
        pkg.version = gitrepo.read_current_branch(clone_path) or pkg.version

        method, build_cmd = detect_build_method(clone_path)
        pkg.build_method = method.value
        watcher.change_substatus(self.i18n['github.build_detected'].format(
            bold(self._method_label(method))))

        if self._is_clone_only():
            watcher.show_message(title=self.i18n['github.clone_only'],
                                 body=self.i18n['github.clone_only.body'].format(
                                     bold(clone_path)),
                                 type_=MessageType.INFO)
            return TransactionResult(success=True, installed=[pkg], removed=[])

        if not is_supported(method):
            watcher.show_message(title=self.i18n['github.unsupported_build'],
                                 body=self.i18n['github.unsupported_build.body'].format(
                                     bold(self._method_label(method)), bold(clone_path)),
                                 type_=MessageType.WARNING)
            return TransactionResult(success=True, installed=[pkg], removed=[])

        return self._build_and_install(pkg, clone_path, method, build_cmd, root_password,
                                       handler, watcher)

    def _clone_or_update(self, pkg: GitHubPackage, clone_path: str, handler: ProcessHandler,
                         watcher: ProcessWatcher) -> bool:
        if os.path.exists(clone_path):
            existing_url = gitrepo.read_remote_url(clone_path)

            if existing_url and pkg.repo_url and \
                    not gitrepo.same_repository(existing_url, pkg.repo_url):
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.path_conflict'].format(
                                         bold(clone_path), bold(existing_url)),
                                     type_=MessageType.ERROR)
                return False

            watcher.change_substatus(self.i18n['github.pulling'].format(bold(pkg.repo_name)))
            success, _ = handler.handle_simple(SimpleProcess(['git', 'pull', '--ff-only'],
                                                             cwd=clone_path))
        else:
            clone_url = self._clone_url(pkg)

            if not clone_url:
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.invalid_repo'].format(
                                         bold(f'{pkg.owner}/{pkg.repo_name}')),
                                     type_=MessageType.ERROR)
                return False

            watcher.change_substatus(self.i18n['github.cloning'].format(bold(clone_url)))
            # el directorio del propietario se crea aquí, nunca en prepare()
            Path(os.path.dirname(clone_path)).mkdir(parents=True, exist_ok=True)
            success, _ = handler.handle_simple(SimpleProcess(['git', 'clone', '--',
                                                              clone_url, clone_path]))

        if not success:
            watcher.show_message(title=self.i18n['github.clone_error'],
                                 body=self.i18n['github.clone_error.body'].format(
                                     bold(pkg.repo_url or clone_path)),
                                 type_=MessageType.ERROR)

        return success

    def _confirm_build(self, pkg: GitHubPackage, clone_path: str, method: BuildMethod,
                       commands: List[str], watcher: ProcessWatcher) -> bool:
        body = '<br/>'.join((
            self.i18n['github.confirm_build.repo'].format(bold(pkg.repo_url or pkg.name)),
            self.i18n['github.confirm_build.path'].format(bold(clone_path)),
            self.i18n['github.confirm_build.method'].format(bold(self._method_label(method))),
            self.i18n['github.confirm_build.commands'].format(
                bold(' &amp;&amp; '.join(commands))),
            '',
            self.i18n['github.confirm_build.warning'],
        ))

        return watcher.request_confirmation(title=self.i18n['github.confirm_build'],
                                            body=body,
                                            confirmation_label=self.i18n['continue'].capitalize(),
                                            deny_label=self.i18n['cancel'].capitalize())

    def _build_and_install(self, pkg: GitHubPackage, clone_path: str, method: BuildMethod,
                           build_cmd: Optional[str], root_password: Optional[str],
                           handler: ProcessHandler,
                           watcher: ProcessWatcher) -> TransactionResult:
        binary = get_required_binary(method)

        if binary and not shutil.which(binary):
            if method == BuildMethod.PYTHON_SETUP:
                # PEP 668: el intérprete del sistema está gestionado externamente y bauh
                # nunca usará '--break-system-packages' para saltárselo
                body = self.i18n['github.missing_pipx.body']
            else:
                body = self.i18n['github.missing_tool.body']

            watcher.show_message(title=self.i18n['github.missing_tool'],
                                 body=body.format(bold(binary), bold(clone_path)),
                                 type_=MessageType.WARNING)
            return TransactionResult(success=True, installed=[pkg], removed=[])

        if not build_cmd:
            return TransactionResult(success=True, installed=[pkg], removed=[])

        build_args = shlex.split(build_cmd)
        displayed = [build_cmd]

        if method == BuildMethod.PKGBUILD:
            displayed.append('sudo pacman -U <*.pkg.tar.zst>')

        if not self._confirm_build(pkg, clone_path, method, displayed, watcher):
            self.logger.info(f"El usuario canceló la construcción de {pkg.repo_url}")
            return TransactionResult(success=True, installed=[pkg], removed=[])

        watcher.change_substatus(self.i18n['github.building'].format(
            bold(pkg.repo_name), bold(self._method_label(method))))

        # la construcción JAMÁS recibe root_password: makepkg se niega a correr como root y
        # el resto de métodos instalan en el HOME del usuario
        build_success, build_output = handler.handle_simple(
            SimpleProcess(build_args, cwd=clone_path))

        if not build_success:
            watcher.show_message(title=self.i18n['github.build_error'],
                                 body=self.i18n['github.build_error.body'].format(
                                     bold(pkg.repo_name), bold(clone_path)),
                                 type_=MessageType.ERROR)
            # el clon se conserva, pero la transacción NO se reporta como instalada
            return TransactionResult.fail()

        artifacts = self._install_artifacts(pkg, clone_path, method, build_output,
                                            root_password, handler, watcher)

        if artifacts is None:
            return TransactionResult.fail()

        pkg.built = True
        pkg.installed_artifacts = artifacts
        self.registry.record(registry.InstallationRegistry.key_for(pkg.owner, pkg.repo_name),
                             method.value, artifacts, clone_path, pkg.repo_url)

        return TransactionResult(success=True, installed=[pkg], removed=[])

    def _install_artifacts(self, pkg: GitHubPackage, clone_path: str, method: BuildMethod,
                           build_output: str, root_password: Optional[str],
                           handler: ProcessHandler,
                           watcher: ProcessWatcher) -> Optional[List[str]]:
        """Ejecuta el paso de instalación y devuelve los artefactos registrados.

        Devuelve ``None`` si el paso falla.
        """
        if method == BuildMethod.PKGBUILD:
            built_files = sorted(f for f in glob.glob(os.path.join(clone_path, '*.pkg.tar*'))
                                 if not f.endswith('.sig'))

            if not built_files:
                watcher.show_message(title=self.i18n['github.build_error'],
                                     body=self.i18n['github.no_package_file'].format(
                                         bold(clone_path)),
                                     type_=MessageType.ERROR)
                return None

            watcher.change_substatus(self.i18n['github.installing_package'].format(
                bold(pkg.repo_name)))

            success, _ = handler.handle_simple(
                SimpleProcess(['pacman', '-U', '--noconfirm', *built_files],
                              root_password=root_password))

            if not success:
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.install_error'].format(
                                         bold(pkg.repo_name)),
                                     type_=MessageType.ERROR)
                return None

            return registry.parse_pacman_package_names(built_files)

        if method == BuildMethod.PYTHON_SETUP:
            return registry.parse_pipx_installed_names(build_output) or [pkg.repo_name]

        if method == BuildMethod.CARGO:
            names = registry.parse_cargo_installed_names(build_output)

            if not names:
                cargo_toml = os.path.join(clone_path, 'Cargo.toml')

                try:
                    with open(cargo_toml, encoding='utf-8', errors='replace') as file:
                        name = registry.read_cargo_package_name(file.read())
                except OSError:
                    name = None

                names = [name] if name else [pkg.repo_name]

            return names

        return []

    # ------------------------------------------------------------------ desinstalación

    def uninstall(self, pkg: GitHubPackage, root_password: Optional[str],
                  watcher: ProcessWatcher, disk_loader: Optional[DiskCacheLoader] = None) -> TransactionResult:
        handler = ProcessHandler(watcher)
        repos_dir = self._get_repos_dir()
        key = registry.InstallationRegistry.key_for(pkg.owner, pkg.repo_name)
        record = self.registry.get(key) or {}

        method = method_from_value(record.get('build_method') or pkg.build_method)
        artifacts = record.get('artifacts') or pkg.installed_artifacts
        command = uninstall_command(method, artifacts)

        if command:
            watcher.change_substatus(self.i18n['github.uninstalling'].format(
                bold(', '.join(artifacts))))
            password = root_password if uninstall_requires_root(method) else None
            success, _ = handler.handle_simple(SimpleProcess(command, root_password=password))

            if not success:
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.uninstall_error'].format(
                                         bold(' '.join(command))),
                                     type_=MessageType.ERROR)
                return TransactionResult.fail()

        clone_path = pkg.clone_path

        if clone_path and os.path.isdir(clone_path):
            if not paths.is_safe_clone_path(repos_dir, clone_path):
                self.logger.error(f"Se rechaza borrar '{clone_path}': queda fuera de "
                                  f"'{repos_dir}' o no es un clon de git")
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.unsafe_path'].format(
                                         bold(clone_path)),
                                     type_=MessageType.ERROR)
                return TransactionResult.fail()

            watcher.change_substatus(self.i18n['github.removing'].format(
                bold(pkg.repo_name or pkg.name)))

            try:
                shutil.rmtree(clone_path)
                self._prune_owner_dir(repos_dir, clone_path)
            except Exception:
                self.logger.error(f"No se pudo eliminar el directorio {clone_path}")
                self.logger.error(traceback.format_exc())
                watcher.show_message(title=self.i18n['error'],
                                     body=self.i18n['github.remove_error'].format(
                                         bold(clone_path)),
                                     type_=MessageType.ERROR)
                return TransactionResult.fail()

        self.registry.remove(key)
        pkg.installed, pkg.cloned, pkg.built = False, False, False

        return TransactionResult(success=True, installed=[], removed=[pkg])

    def _prune_owner_dir(self, repos_dir: str, clone_path: str):
        """Elimina el directorio del propietario si se ha quedado vacío."""
        owner_dir = os.path.dirname(clone_path)

        if not paths.is_inside(repos_dir, owner_dir):
            return

        try:
            if not os.listdir(owner_dir):
                os.rmdir(owner_dir)
        except OSError:
            pass

    def downgrade(self, pkg: SoftwarePackage, root_password: Optional[str],
                  handler: ProcessWatcher) -> bool:
        return False

    def upgrade(self, requirements: UpgradeRequirements, root_password: Optional[str],
                watcher: ProcessWatcher) -> bool:
        """Actualiza los clones con ``git pull``.

        No se reconstruye automáticamente: volver a compilar ejecuta código de terceros y
        exige la confirmación explícita del usuario, así que se le indica que reinstale.
        """
        handler = ProcessHandler(watcher)
        success = True

        for req in (requirements.to_upgrade or []):
            pkg = req.pkg

            if not isinstance(pkg, GitHubPackage) or not pkg.clone_path \
                    or not os.path.isdir(pkg.clone_path):
                continue

            watcher.change_substatus(self.i18n['github.pulling'].format(bold(pkg.repo_name)))
            pulled, _ = handler.handle_simple(SimpleProcess(['git', 'pull', '--ff-only'],
                                                            cwd=pkg.clone_path))

            if not pulled:
                success = False
                continue

            if pkg.built:
                watcher.print(self.i18n['github.rebuild_needed'].format(pkg.repo_name))

        return success

    def get_managed_types(self) -> Set[Type[SoftwarePackage]]:
        return {GitHubPackage}

    def get_info(self, pkg: GitHubPackage) -> dict:
        method = method_from_value(pkg.build_method)
        yes, no = self.i18n['yes'].capitalize(), self.i18n['no'].capitalize()

        info = {
            self.i18n['github.info.name']: pkg.name,
            self.i18n['github.info.owner']: pkg.owner or '-',
            self.i18n['github.info.url']: pkg.repo_url or '-',
            self.i18n['github.info.stars']: str(pkg.stars) if pkg.stars else '-',
            self.i18n['github.info.language']: pkg.language or '-',
            self.i18n['github.info.license']: pkg.license or '-',
            self.i18n['github.info.branch']: pkg.version or pkg.default_branch or '-',
            self.i18n['github.info.build']: self._method_label(method),
            self.i18n['github.info.cloned']: yes if pkg.cloned else no,
            self.i18n['github.info.built']: yes if pkg.built else no,
            self.i18n['github.info.path']: pkg.clone_path or '-',
        }

        if pkg.installed_artifacts:
            info[self.i18n['github.info.artifacts']] = ', '.join(pkg.installed_artifacts)

        return info

    def get_history(self, pkg: SoftwarePackage) -> PackageHistory:
        return PackageHistory(pkg=pkg, history=[], pkg_status_idx=-1)

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def can_work(self) -> Tuple[bool, Optional[str]]:
        if not shutil.which('git'):
            return False, self.i18n['github.requires_git']

        return True, None

    def requires_root(self, action: SoftwareAction, pkg: Optional[SoftwarePackage] = None) -> bool:
        if not isinstance(pkg, GitHubPackage):
            return False

        if action == SoftwareAction.INSTALL:
            if self._is_clone_only():
                return False

            if pkg.clone_path and os.path.isdir(pkg.clone_path):
                method, _ = detect_build_method(pkg.clone_path)
                return build_requires_root(method)

            # el repositorio aún no está clonado: no se sabe el método, así que se pide la
            # contraseña por si hiciera falta un 'pacman -U' al final (F03)
            return True

        if action == SoftwareAction.UNINSTALL:
            record = self.registry.get(
                registry.InstallationRegistry.key_for(pkg.owner, pkg.repo_name)) or {}
            method = method_from_value(record.get('build_method') or pkg.build_method)
            return uninstall_requires_root(method) and bool(record.get('artifacts')
                                                            or pkg.installed_artifacts)

        return False

    def prepare(self, task_manager: Optional[TaskManager], root_password: Optional[str],
                internet_available: Optional[bool]):
        # el directorio de repositorios se crea perezosamente al instalar: crearlo aquí
        # sembraba una carpeta en el HOME de todo el mundo aunque la gem no se usara
        pass

    def list_updates(self, internet_available: bool) -> List[PackageUpdate]:
        if not internet_available or not self._get_config().get('check_updates', True):
            return []

        updates = []

        for clone_path in self._iter_clone_dirs(self._get_repos_dir()):
            self._run_git(['fetch', '--quiet'], clone_path)
            behind = self._count_commits_behind(clone_path)

            if behind <= 0:
                continue

            repo_url = gitrepo.read_remote_url(clone_path)
            parsed = gitrepo.parse_github_url(repo_url) if repo_url else None
            name = parsed[1] if parsed else os.path.basename(clone_path)

            updates.append(PackageUpdate(pkg_id=repo_url or clone_path,
                                         version=str(behind),
                                         pkg_type='GitHub',
                                         name=name))

        return updates

    def list_warnings(self, internet_available: bool) -> Optional[List[str]]:
        warnings = []

        if not internet_available:
            warnings.append(self.i18n['github.no_internet'])
        elif self._api_warning:
            warnings.append(self.i18n[self._api_warning])

        return warnings if warnings else None

    def is_default_enabled(self) -> bool:
        # la gem no forma parte del alcance oficial del fork: es opt-in
        return False

    def launch(self, pkg: SoftwarePackage):
        if isinstance(pkg, GitHubPackage) and pkg.clone_path and os.path.isdir(pkg.clone_path):
            try:
                subprocess.Popen(['xdg-open', pkg.clone_path])
            except Exception:
                self.logger.error(f"No se pudo abrir el directorio {pkg.clone_path}")
                self.logger.error(traceback.format_exc())

    def get_screenshots(self, pkg: SoftwarePackage) -> Generator[str, None, None]:
        yield from ()

    def clear_data(self, logs: bool = True):
        """Elimina la caché y el registro de la gem.

        Los clones NO se borran: son código fuente del usuario, no datos de bauh, y
        eliminarlos sin confirmación podría destruir trabajo local.
        """
        self._api_cache.clear()

        if os.path.exists(GITHUB_CACHE_DIR):
            try:
                shutil.rmtree(GITHUB_CACHE_DIR)

                if logs:
                    self.logger.info(f"Directorio de caché eliminado: {GITHUB_CACHE_DIR}")
            except Exception:
                if logs:
                    self.logger.error(f"No se pudo eliminar el directorio {GITHUB_CACHE_DIR}")
                    self.logger.error(traceback.format_exc())

        if logs:
            self.logger.info(f"Los repositorios clonados en '{self._get_repos_dir()}' se "
                             f"conservan: contienen código fuente del usuario")

    # ------------------------------------------------------------------ ajustes

    def get_settings(self) -> Optional[Generator[SettingsView, None, None]]:
        config = self._get_config()
        yes_label, no_label = self.i18n['yes'].capitalize(), self.i18n['no'].capitalize()

        repos_dir = config.get('repos_dir') or DEFAULT_REPOS_DIR

        fields = [
            FileChooserComponent(label=self.i18n['github.config.repos_dir'],
                                 tooltip=self.i18n['github.config.repos_dir.tip'],
                                 file_path=os.path.expanduser(str(repos_dir)),
                                 search_path=os.path.expanduser(str(repos_dir)),
                                 directory=True,
                                 id_='repos_dir'),
            new_select(label=self.i18n['github.config.clone_only'],
                       tip=self.i18n['github.config.clone_only.tip'],
                       id_='clone_only',
                       opts=((yes_label, True, None), (no_label, False, None)),
                       value=bool(config.get('clone_only', True))),
            new_select(label=self.i18n['github.config.search_enabled'],
                       tip=self.i18n['github.config.search_enabled.tip'],
                       id_='search_enabled',
                       opts=((yes_label, True, None), (no_label, False, None)),
                       value=bool(config.get('search_enabled', False))),
            TextInputComponent(label=self.i18n['github.config.search_limit'],
                               tooltip=self.i18n['github.config.search_limit.tip'],
                               value=str(config.get('search_limit', DEFAULT_SEARCH_LIMIT)),
                               only_int=True,
                               id_='search_limit'),
            new_select(label=self.i18n['github.config.check_updates'],
                       tip=self.i18n['github.config.check_updates.tip'],
                       id_='check_updates',
                       opts=((yes_label, True, None), (no_label, False, None)),
                       value=bool(config.get('check_updates', True))),
            TextInputComponent(label=self.i18n['github.config.token'],
                               tooltip=self.i18n['github.config.token.tip'],
                               value=str(config.get('github_token') or ''),
                               id_='github_token'),
        ]

        yield SettingsView(self, PanelComponent([FormComponent(fields, self.i18n['github.config'])]),
                           icon_path=get_icon_path())

    def save_settings(self, component: PanelComponent) -> Tuple[bool, Optional[List[str]]]:
        config = self._get_config()
        form = component.get_component_by_idx(0, FormComponent)

        repos_dir = form.get_component('repos_dir', FileChooserComponent).file_path
        config['repos_dir'] = repos_dir if repos_dir else DEFAULT_REPOS_DIR

        for key in ('clone_only', 'search_enabled', 'check_updates'):
            config[key] = bool(form.get_component(key, SingleSelectComponent).get_selected())

        try:
            search_limit = int(form.get_component('search_limit',
                                                  TextInputComponent).get_value())
        except (TypeError, ValueError):
            search_limit = DEFAULT_SEARCH_LIMIT

        config['search_limit'] = search_limit if search_limit > 0 else DEFAULT_SEARCH_LIMIT

        token = form.get_component('github_token', TextInputComponent).get_value().strip()
        config['github_token'] = token if token else None

        try:
            self.configman.save_config(config)
            self._api_cache.clear()
            return True, None
        except Exception:
            return False, [traceback.format_exc()]

    # ------------------------------------------------------------------ compatibilidad

    def migrate_legacy_repos_dir(self) -> Optional[str]:
        """Devuelve el directorio heredado ``~/BauhRepos`` si aún contiene clones.

        No se mueve nada automáticamente; el valor sirve para avisar al usuario.
        """
        if os.path.isdir(LEGACY_REPOS_DIR) and os.listdir(LEGACY_REPOS_DIR):
            return LEGACY_REPOS_DIR

        return None
