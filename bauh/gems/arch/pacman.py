import logging
import os
import re
import shutil
import subprocess
import traceback
from threading import Thread
from typing import List, Sequence, Set, Tuple, Dict, Iterable, Optional, Any, Pattern, Collection

from colorama import Fore

from bauh.commons import system
from bauh.commons.system import new_subprocess, new_root_subprocess, SystemProcess, SimpleProcess
from bauh.commons.util import size_to_byte
from bauh.gems.arch.exceptions import PackageNotFoundException, PackageInHoldException

RE_DEPS = re.compile(r'[\w\-_]+:[\s\w_\-.]+\s+\[\w+]')
RE_OPTDEPS = re.compile(r'[\w._\-]+\s*:')
RE_DEP_NOTFOUND = re.compile(r'error:.+\'(.+)\'')
RE_DEP_OPERATORS = re.compile(r'[<>=]')
RE_REPOSITORY_FIELDS = re.compile(r'(Repository|Name|Description|Version|Install Date|Validated By)\s*:\s*(.+)')
RE_INSTALLED_SIZE = re.compile(r'Installed Size\s*:\s*([0-9,.]+)\s(\w+)\n?', re.IGNORECASE)
RE_DOWNLOAD_SIZE = re.compile(r'Download Size\s*:\s*([0-9,.]+)\s(\w+)\n?', re.IGNORECASE)
RE_UPDATE_REQUIRED_FIELDS = re.compile(r'(\bProvides\b|\bInstalled Size\b|\bConflicts With\b)\s*:\s(.+)\n')
RE_REMOVE_TRANSITIVE_DEPS = re.compile(r'removing\s([\w\-_]+)\s.+required\sby\s([\w\-_]+)\n?')
RE_AVAILABLE_MIRRORS = re.compile(r'.+\s+OK\s+.+\s+(\d+:\d+)\s+.+(http.+)')
RE_PACMAN_SYNC_FIRST = re.compile(r'SyncFirst\s*=\s*(.+)')
RE_DESKTOP_FILES = re.compile(r'\n?([\w\-_]+)\s+(/usr/share/.+\.desktop)')
# secciones de repositorio de pacman.conf: admite guiones ([chaotic-aur], [core-testing]...)
RE_PACMAN_REPOSITORY_SECTION = re.compile(r'^[ \t]*\[([^]\s]+)][ \t]*$', re.MULTILINE)
# linea de resultado de 'pacman -Ss': "repositorio/paquete version"
RE_SEARCH_RESULT_LINE = re.compile(r'^([^/\s]+)/(\S+)\s')
# linea de conflicto de ficheros de pacman: "paquete: /ruta/al/fichero exists in filesystem"
RE_CONFLICTING_FILE = re.compile(r'^\s*[^\s:]+:\s+(/\S+)\s+exists in filesystem')
RE_INFO_NAME = re.compile(r'^Name\s*:\s*(\S+)\s*$')
RE_INFO_REPOSITORY = re.compile(r'^Repository\s*:\s*(\S+)\s*$')
RE_IGNORED_PACKAGES: Optional[Pattern] = None


def _run(args: Sequence[str], expected_code: int = 0, ignore_return_code: bool = False,
         print_error: bool = True, custom_env: Optional[dict] = None) -> Optional[str]:
    """
    Ejecuta un comando pasando los argumentos como lista (sin shell) y devuelve su salida estandar.

    Sustituye a 'bauh.commons.system.run_cmd', que concatena cadenas y ejecuta con 'shell=True':
    los nombres de paquete y el texto del buscador llegan desde la interfaz y desde ficheros
    .SRCINFO de terceros, asi que no deben interpretarse nunca como ordenes de shell.
    """
    final_args = [a for a in args if a]

    if not final_args:
        return None

    params = {'stdout': subprocess.PIPE,
              'env': custom_env if custom_env is not None else system.gen_env(),
              'cwd': '.',
              'shell': False}

    if not print_error:
        params['stderr'] = subprocess.DEVNULL

    res = subprocess.run(final_args, check=False, **params)

    if ignore_return_code or res.returncode == expected_code:
        try:
            return res.stdout.decode()
        except UnicodeDecodeError:
            return None


def _execute(args: Sequence[str], custom_env: Optional[dict] = None) -> Tuple[int, Optional[str]]:
    """
    Ejecuta un comando como lista de argumentos (sin shell) y devuelve el codigo de retorno
    junto a la salida (stderr incluido), igual que 'bauh.commons.system.execute'.
    """
    final_args = [a for a in args if a]

    if not final_args:
        return 1, None

    params = {'stdout': subprocess.PIPE,
              'stderr': subprocess.STDOUT,
              'shell': False}

    if custom_env is not None:
        params['env'] = custom_env

    proc = subprocess.run(final_args, check=False, **params)

    output = None
    if proc.stdout:
        try:
            output = proc.stdout.decode()
        except UnicodeDecodeError:
            output = None

    return proc.returncode, output


def list_conflicting_files(output: str) -> List[str]:
    """
    Extrae de la salida de pacman las rutas de los ficheros en conflicto para poder pasarlas
    a '--overwrite' de forma acotada en lugar de usar el comodin '*'.
    """
    if not output:
        return []

    paths, added = [], set()

    for line in output.split('\n'):
        match = RE_CONFLICTING_FILE.match(line)

        if match:
            path = match.group(1)

            if path not in added:
                added.add(path)
                paths.append(path)

    return paths


def map_repositories_from_info(output: Optional[str]) -> Dict[str, str]:
    """
    Asocia cada paquete de una salida de 'pacman -Si' con el repositorio que lo provee.
    """
    res = {}

    if output:
        current_repository = None

        for line in output.split('\n'):
            repository_match = RE_INFO_REPOSITORY.match(line)

            if repository_match:
                current_repository = repository_match.group(1)
                continue

            name_match = RE_INFO_NAME.match(line)

            if name_match and current_repository:
                res[name_match.group(1)] = current_repository
                current_repository = None

    return res


def map_available_repositories(pkgnames: Collection[str]) -> Dict[str, str]:
    """
    Devuelve {paquete: repositorio} con los nombres recibidos que existan en algun repositorio
    binario habilitado en pacman.conf.

    Funciona con cualquier repositorio de pacman (core, extra, multilib, chaotic-aur,
    repositorios propios...), no solo con Chaotic AUR.
    """
    if not pkgnames:
        return {}

    output = _run(['pacman', '-Si', *sorted(pkgnames)], print_error=False, ignore_return_code=True)
    return map_repositories_from_info(output)


def list_running_pacman_pids(proc_dir: str = '/proc') -> Set[int]:
    """
    Devuelve los PID de los procesos 'pacman' en ejecucion leyendo /proc.

    Se usa antes de ofrecer el borrado de /var/lib/pacman/db.lck: si hay una transaccion viva,
    eliminar el bloqueo permitiria dos transacciones simultaneas y corromper la base de datos.
    """
    pids = set()

    try:
        entries = os.listdir(proc_dir)
    except OSError:
        return pids

    for entry in entries:
        if not entry.isdigit():
            continue

        try:
            with open(f'{proc_dir}/{entry}/comm') as f:
                if f.read().strip() == 'pacman':
                    pids.add(int(entry))
        except (OSError, ValueError):
            continue

    return pids


def is_available() -> bool:
    return bool(shutil.which('pacman'))


def get_repositories(pkgs: Iterable[str]) -> dict:
    """
    Devuelve {paquete: repositorio} para los nombres recibidos.

    La asociacion se hace por nombre exacto: buscar por subcadena atribuia el repositorio de
    'zlib-ng' al paquete 'zlib' (o el de 'linux-headers' a 'linux').
    """
    pkgnames = tuple(p for p in pkgs if p)

    if not pkgnames:
        return {}

    pkgre = '|'.join(pkgnames).replace('+', r'\+').replace('.', r'\.')

    wanted = {*pkgnames}
    repositories = {}

    for line in new_subprocess(['pacman', '-Ss', pkgre]).stdout:
        if line:
            try:
                match = RE_SEARCH_RESULT_LINE.match(line.decode())
            except UnicodeDecodeError:
                continue

            if match and match.group(2) in wanted:
                repositories[match.group(2)] = match.group(1)

    not_found = {pkg for pkg in pkgnames if pkg not in repositories}

    if not_found:  # if there are some packages not found, try to find via the single method:
        for dep in not_found:
            repo_data = guess_repository(dep)

            if repo_data:
                repositories[repo_data[0]] = repo_data[1]

    return repositories


def get_info(pkg_name, remote: bool = False) -> str:
    return _run(['pacman', '-{}i'.format('Q' if not remote else 'S'), pkg_name], print_error=False)


def get_info_list(pkg_name: str, remote: bool = False) -> List[tuple]:
    info = get_info(pkg_name, remote)
    if info:
        return re.findall(r'(\w+\s?\w+)\s*:\s*(.+(\n\s+.+)*)', info)


def get_info_dict(pkg_name: str, remote: bool = False) -> Optional[dict]:
    list_attrs = {'depends on', 'required by', 'conflicts with'}
    info_list = get_info_list(pkg_name, remote)

    if info_list:
        info_dict = {}
        for info_data in info_list:
            attr = info_data[0].lower().strip()
            info_dict[attr] = info_data[1]

            if info_dict[attr] == 'None':
                info_dict[attr] = None

            if attr == 'optional deps' and info_dict[attr]:
                info_dict[attr] = info_dict[attr].split('\n')
            elif attr in list_attrs and info_dict[attr]:
                info_dict[attr] = [d.strip() for d in info_dict[attr].split(' ') if d]

        return info_dict


def check_installed(pkg: str) -> bool:
    res = _run(['pacman', '-Qq', pkg], print_error=False)
    return bool(res)


def fill_ignored_packages(output: Set[str]):
    output.update(list_ignored_packages())


def map_packages(names: Optional[Iterable[str]] = None, remote: bool = False, signed: bool = True,
                 not_signed: bool = True, skip_ignored: bool = False) -> Dict[str, Dict[str, Dict[str, str]]]:
    if not signed and not not_signed:
        return {}

    ignored, thread_ignored = None, None
    if not skip_ignored:
        ignored = set()
        thread_ignored = Thread(target=fill_ignored_packages, args=(ignored,), daemon=True)
        thread_ignored.start()

    env = system.gen_env()
    env['LC_TIME'] = ''

    code, allinfo = _execute(['pacman', f"-{'S' if remote else 'Q'}i", *(names if names else ())],
                             custom_env=env)

    pkgs = {'signed': {}, 'not_signed': {}}

    if code == 0 and allinfo:
        current_pkg = {}

        for idx, field_tuple in enumerate(RE_REPOSITORY_FIELDS.findall(allinfo)):
            if field_tuple[0].startswith('R'):
                current_pkg['repository'] = field_tuple[1].strip()
            elif field_tuple[0].startswith('N'):
                current_pkg['name'] = field_tuple[1].strip()
            elif field_tuple[0].startswith('Ve'):
                current_pkg['version'] = field_tuple[1].strip()
            elif field_tuple[0].startswith('D'):
                current_pkg['description'] = field_tuple[1].strip()
            elif field_tuple[0].startswith('I'):
                current_pkg['install_date'] = field_tuple[1].strip()
            elif field_tuple[0].startswith('Va'):
                if not_signed and field_tuple[1].strip().lower() == 'none':
                    pkgs['not_signed'][current_pkg['name']] = current_pkg
                    del current_pkg['name']
                elif signed:
                    pkgs['signed'][current_pkg['name']] = current_pkg
                    del current_pkg['name']

                current_pkg = {}

    if thread_ignored and (pkgs['signed'] or pkgs['not_signed']):
        thread_ignored.join()

        if ignored:
            for key in ('signed', 'not_signed'):
                if pkgs.get(key):
                    to_del = set()
                    for pkg in pkgs[key].keys():
                        if pkg in ignored:
                            to_del.add(pkg)

                    for pkg in to_del:
                        del pkgs[key][pkg]
    return pkgs


def install_as_process(pkgpaths: Iterable[str], root_password: Optional[str], file: bool, pkgdir: str = '.',
                       overwrite_conflicting_files: bool = False, simulate: bool = False, as_deps: bool = False,
                       conflicting_files: Optional[Collection[str]] = None) -> SimpleProcess:
    """
    Genera el proceso de instalacion.

    '-dd' (omitir por completo la comprobacion de dependencias de pacman) solo se aplica a
    'pacman -U', es decir a los paquetes recien compilados desde el AUR cuyas dependencias ya
    resolvio e instalo bauh antes (makepkg construye con --nodeps). En la instalacion desde
    repositorio ('pacman -S') se deja que pacman verifique las dependencias: es su terreno y
    evita dejar el sistema con dependencias insatisfechas si el resolvedor propio se equivoca.

    'conflicting_files' limita '--overwrite' a las rutas detectadas en la salida del intento
    anterior; solo se recurre al comodin '*' si no se pudo determinar ninguna.
    """
    cmd = ['pacman', '-U'] if file else ['pacman', '-S']
    cmd.extend(pkgpaths)

    if simulate:
        cmd.append('--confirm')
    else:
        cmd.append('--noconfirm')

        if file:
            cmd.append('-dd')

    if overwrite_conflicting_files:
        if conflicting_files:
            cmd.extend(f'--overwrite={path}' for path in conflicting_files)
        else:
            cmd.append('--overwrite=*')

    if as_deps:
        cmd.append('--asdeps')

    return SimpleProcess(cmd=cmd,
                         root_password=root_password,
                         cwd=pkgdir,
                         error_phrases={"error: failed to prepare transaction", 'error: failed to commit transaction', 'error: target not found'},
                         shell=False)


def map_desktop_files(*pkgnames) -> Dict[str, List[str]]:
    res = {}

    if pkgnames:
        output = _run(['pacman', '-Ql', *pkgnames], print_error=False)

        if output:
            for match in RE_DESKTOP_FILES.findall(output):
                pkgfiles = res.get(match[0], [])
                res[match[0]] = pkgfiles
                pkgfiles.append(match[1])

    return res


def list_installed_files(pkgname: str) -> List[str]:
    installed_files = _run(['pacman', '-Qlq', pkgname], print_error=False)

    paths = []

    if installed_files:
        for f in installed_files.split('\n'):
            if f:
                f_strip = f.strip()

                if f_strip and not f_strip.endswith('/'):
                    paths.append(f_strip)

    return paths


def verify_pgp_key(key: str) -> bool:
    list_key = new_subprocess(['pacman-key', '-l']).stdout

    for out in new_subprocess(['grep', " " + key], stdin=list_key).stdout:
        if out:
            line = out.decode().strip()
            if line and key in line:
                return True

    return False


def receive_key(key: str, root_password: Optional[str]) -> SystemProcess:
    return SystemProcess(new_root_subprocess(['pacman-key', '-r', key], root_password=root_password), check_error_output=False)


def sign_key(key: str, root_password: Optional[str]) -> SystemProcess:
    return SystemProcess(new_root_subprocess(['pacman-key', '--lsign-key', key], root_password=root_password), check_error_output=False)


def list_ignored_packages(config_path: str = '/etc/pacman.conf') -> Set[str]:
    ignored = set()

    try:
        with open(config_path, 'r') as f:
            file_content = f.read()

        global RE_IGNORED_PACKAGES

        if not RE_IGNORED_PACKAGES:
            RE_IGNORED_PACKAGES = re.compile(r'[\s#]*ignorepkg\s*=\s*.+', re.IGNORECASE)

        for raw_line in RE_IGNORED_PACKAGES.findall(file_content):
            line = raw_line.strip()

            if line and not line.startswith("#"):
                ignored.add(line.split("=")[1].strip())
    except (FileNotFoundError, OSError):
        pass
    except Exception:
        import logging; logging.error("Exception occurred", exc_info=True)

    return ignored


def check_missing(names: Set[str]) -> Set[str]:
    installed = new_subprocess(['pacman', '-Qq', *names])

    not_installed = set()

    for o in installed.stderr:
        if o:
            err_line = o.decode()

            if err_line:
                not_found = [n for n in RE_DEP_NOTFOUND.findall(err_line) if n]

                if not_found:
                    not_installed.update(not_found)

    return not_installed


def read_repository_from_info(name: str) -> Optional[str]:
    info = new_subprocess(['pacman', '-Si', name])

    not_found = False
    for o in info.stderr:
        if o:
            err_line = o.decode()
            if RE_DEP_NOTFOUND.findall(err_line):
                not_found = True

    if not_found:
        return

    repository = None

    for o in new_subprocess(['grep', '-Po', r"Repository\s+:\s+\K.+"], stdin=info.stdout).stdout:
        if o:
            line = o.decode().strip()

            if line:
                repository = line

    return repository


def guess_repository(name: str) -> Tuple[str, str]:
    if not name:
        raise Exception("'name' cannot be None or blank")

    only_name = RE_DEP_OPERATORS.split(name)[0]
    res = _run(['pacman', '-Ss', only_name])

    if res:
        lines = res.split('\n')

        if lines:
            for line in lines:
                if line and not line.startswith(' '):
                    data = line.split('/')
                    line_name, line_repo = data[1].split(' ')[0], data[0]

                    provided = read_provides(line_name)

                    if provided:
                        found = {p for p in provided if only_name == RE_DEP_OPERATORS.split(p)[0]}

                        if found:
                            return line_name, line_repo


def read_provides(name: str) -> Set[str]:
    dep_info = new_subprocess(['pacman', '-Si', name])

    not_found = False

    for o in dep_info.stderr:
        if o:
            err_line = o.decode()

            if err_line:
                if RE_DEP_NOTFOUND.findall(err_line):
                    not_found = True

    if not_found:
        raise PackageNotFoundException(name)

    provides = None

    for out in new_subprocess(['grep', '-Po', r'Provides\s+:\s\K(.+)'], stdin=dep_info.stdout).stdout:
        if out:
            provided_names = [p.strip() for p in out.decode().strip().split(' ') if p]

            if provided_names[0].lower() == 'none':
                provides = {name}
            else:
                provides = {name, *provided_names}

    return provides


def read_dependencies(name: str) -> Set[str]:
    dep_info = new_subprocess(['pacman', '-Si', name])

    not_found = False

    for o in dep_info.stderr:
        if o:
            err_line = o.decode()

            if err_line:
                if RE_DEP_NOTFOUND.findall(err_line):
                    not_found = True

    if not_found:
        raise PackageNotFoundException(name)

    depends_on = set()
    for out in new_subprocess(['grep', '-Po', r'Depends\s+On\s+:\s\K(.+)'], stdin=dep_info.stdout).stdout:
        if out:
            line = out.decode().strip()

            if line:
                depends_on.update([d for d in line.split(' ') if d and d.lower() != 'none'])

    return depends_on


def sync_databases(root_password: Optional[str], force: bool = False) -> SimpleProcess:
    return SimpleProcess(cmd=['pacman', '-Sy{}'.format('y' if force else '')],
                         root_password=root_password)


def get_version_for_not_installed(pkgname: str) -> str:
    output = _run(['pacman', '-Ss', pkgname], print_error=False)

    if output:
        return output.split('\n')[0].split(' ')[1].strip()


def map_repositories(pkgnames: Iterable[str] = None) -> Dict[str, str]:
    info = _run(['pacman', '-Si', *(pkgnames if pkgnames else ())], print_error=False, ignore_return_code=True)
    return map_repositories_from_info(info)


def list_repository_updates() -> Dict[str, str]:
    output = _run(['pacman', '-Qu'])
    res = {}
    if output:
        for line in output.split('\n'):
            if line:
                line_split = line.split(' ')
                res[line_split[0]] = line_split[-1]
    return res


def get_build_date(pkgname: str) -> str:
    output = _run(['pacman', '-Qi', pkgname])

    if output:
        bdate_line = [l for l in output.split('\n') if l.startswith('Build Date')]

        if bdate_line:
            return ':'.join(bdate_line[0].split(':')[1:]).strip()


def search(words: str) -> Dict[str, dict]:
    output = _run(['pacman', '-Ss', *words.split()], print_error=False)

    found = {}
    if output:
        current = {}
        for l in output.split('\n'):
            if l:
                if l.startswith(' '):
                    current['description'] = l.strip()
                    found[current['name']] = current
                    del current['name']
                    current = None
                else:
                    if current is None:
                        current = {}

                    repo_split = l.split('/')
                    current['repository'] = repo_split[0]

                    data_split = repo_split[1].split(' ')
                    current['name'] = data_split[0]

                    current['version'] = data_split[1]
    return found


def get_databases(file_path: str = '/etc/pacman.conf') -> Set[str]:
    """
    Devuelve los repositorios declarados en pacman.conf.

    Reconoce nombres con guion como [chaotic-aur], [core-testing] o [multilib-testing]:
    la expresion anterior solo aceptaba caracteres de palabra y los descartaba.
    """
    try:
        with open(file_path) as f:
            conf_str = f.read()
    except OSError:
        return set()

    return {db for db in RE_PACMAN_REPOSITORY_SECTION.findall(conf_str) if db != 'options'}


def can_refresh_mirrors() -> bool:
    return is_mirrors_available()


def refresh_mirrors(root_password: Optional[str]) -> SimpleProcess:
    return SimpleProcess(cmd=['pacman-mirrors', '-g'], root_password=root_password)


def update_mirrors(root_password: Optional[str], countries: List[str]) -> SimpleProcess:
    return SimpleProcess(cmd=['pacman-mirrors', '-c', ','.join(countries)], root_password=root_password)


def sort_fastest_mirrors(root_password: Optional[str], limit: int) -> SimpleProcess:
    cmd = ['pacman-mirrors', '--fasttrack']

    if limit > 0:
        cmd.append(str(limit))

    return SimpleProcess(cmd=cmd, root_password=root_password)


def list_mirror_countries() -> List[str]:
    output = _run(['pacman-mirrors', '-l'])

    if output:
        return [c for c in output.split('\n') if c]


def get_current_mirror_countries() -> List[str]:
    output = (_run(['pacman-mirrors', '-lc']) or '').strip()
    return ['all'] if not output else [c for c in output.split('\n') if c]


def is_mirrors_available() -> bool:
    return bool(shutil.which('pacman-mirrors'))


def map_update_sizes(pkgs: List[str]) -> Dict[str, float]:  # bytes:
    output = _run(['pacman', '-Si', *pkgs])

    if output:
        return {pkgs[idx]: size_to_byte(size[0], size[1]) for idx, size in enumerate(RE_INSTALLED_SIZE.findall(output))}

    return {}


def map_download_sizes(pkgs: List[str]) -> Dict[str, float]:  # bytes:
    output = _run(['pacman', '-Si', *pkgs])

    if output:
        return {pkgs[idx]: size_to_byte(size[0], size[1]) for idx, size in enumerate(RE_DOWNLOAD_SIZE.findall(output))}

    return {}


def get_installed_size(pkgs: List[str]) -> Dict[str, float]:  # bytes
    output = _run(['pacman', '-Qi', *pkgs])

    if output:
        return {pkgs[idx]: size_to_byte(size[0], size[1]) for idx, size in enumerate(RE_INSTALLED_SIZE.findall(output))}

    return {}


def upgrade_system(root_password: Optional[str]) -> SimpleProcess:
    return SimpleProcess(cmd=['pacman', '-Syyu', '--noconfirm'], root_password=root_password)


def _fill_provided_map(key: str, val: str, output: Dict[str, Set[str]]):
    current_val = output.get(key)

    if current_val is None:
        output[key] = {val}
    else:
        current_val.add(val)


def map_provided(remote: bool = False, pkgs: Iterable[str] = None) -> Optional[Dict[str, Set[str]]]:
    output = _run(['pacman', f"-{'S' if remote else 'Q'}i", *(pkgs if pkgs else ())])

    if output:
        provided_map = {}
        latest_name, latest_version, provided = None, None, False

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()
                    val = line[field_sep_idx + 1:].strip()

                    if field == 'Name':
                        latest_name = val
                    elif field == 'Version':
                        latest_version = val.split('=')[0]
                    elif field == 'Provides':
                        _fill_provided_map(latest_name, latest_name, provided_map)
                        _fill_provided_map(f'{latest_name}={latest_version}', latest_name, provided_map)

                        if val != 'None':
                            for w in val.split(' '):
                                if w:
                                    word = w.strip()
                                    _fill_provided_map(word, latest_name, provided_map)

                                    word_split = word.split('=')

                                    if word_split[0] != word:
                                        _fill_provided_map(word_split[0], latest_name, provided_map)
                        else:
                            provided = True

                    elif provided:
                        latest_name = None
                        latest_version = None
                        provided = False

                elif provided:
                    for w in l.split(' '):
                        if w:
                            word = w.strip()
                            _fill_provided_map(word, latest_name, provided_map)

                            word_split = word.split('=')

                            if word_split[0] != word:
                                _fill_provided_map(word_split[0], latest_name, provided_map)

        return provided_map


def list_download_data(pkgs: Iterable[str]) -> List[Dict[str, str]]:
    _, output = system.run(['pacman', '-Si', *pkgs])

    res = []
    if output:
        data = {'a': None, 'v': None, 'r': None, 'n': None}

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()
                    val = line[field_sep_idx + 1:].strip()

                    if field == 'Repository':
                        data['r'] = val
                    elif field == 'Name':
                        data['n'] = val
                    elif field == 'Version':
                        data['v'] = val.split('=')[0]
                    elif field == 'Architecture':
                        data['a'] = val
                    elif data.get('a'):
                        res.append(data)
                        data = {'a': None, 'v': None, 'r': None, 'n': None}

    return res


def map_updates_data(pkgs: Iterable[str], files: bool = False, description: bool = False) -> Optional[Dict[str, Dict[str, object]]]:
    if pkgs:
        if files:
            output = _run(['pacman', '-Qi', '-p', *pkgs])
        else:
            output = _run(['pacman', '-Si', *pkgs])

        res = {}
        if output:
            latest_name = None
            data = {'ds': None, 's': None, 'v': None, 'c': None, 'p': None, 'd': None, 'r': None, 'des': None}
            latest_field = None

            for l in output.split('\n'):
                if l:
                    if l[0] != ' ':
                        line = l.strip()
                        field_sep_idx = line.index(':')
                        field = line[0:field_sep_idx].strip()
                        val = line[field_sep_idx + 1:].strip()

                        if field == 'Repository':
                            data['r'] = val
                            latest_field = 'r'
                        elif field == 'Name':
                            latest_name = val
                            latest_field = 'n'
                        elif field == 'Version':
                            data['v'] = val.split('=')[0]
                            latest_field = 'v'
                        elif description and field == 'Description':
                            data['des'] = val
                            latest_field = 'des'
                        elif field == 'Provides':
                            latest_field = 'p'
                            data['p'] = {latest_name, '{}={}'.format(latest_name, data['v'])}
                            if val != 'None':
                                for w in val.split(' '):
                                    if w:
                                        word = w.strip()
                                        data['p'].add(word)

                                        word_split = word.split('=')

                                        if word_split[0] != word:
                                            data['p'].add(word_split[0])
                        elif field == 'Depends On':
                            val = val.strip()

                            if val == 'None':
                                data['d'] = None
                            else:
                                data['d'] = {w.strip() for w in val.split(' ') if w}
                                latest_field = 'd'
                        elif field == 'Conflicts With':
                            if val == 'None':
                                data['c'] = None
                            else:
                                data['c'] = {w.strip() for w in val.split(' ') if w}

                            latest_field = 'c'
                        elif field == 'Download Size':
                            size = val.split(' ')
                            data['ds'] = size_to_byte(size[0], size[1])
                            latest_field = 'ds'
                        elif field == 'Installed Size':
                            size = val.split(' ')
                            data['s'] = size_to_byte(size[0], size[1])
                            latest_field = 's'
                        elif latest_name and latest_field == 's':
                            res[latest_name] = data
                            latest_name = None
                            latest_field = None
                            data = {'ds': None, 's': None, 'c': None, 'p': None, 'd': None,
                                    'r': None, 'v': None, 'des': None}
                        else:
                            latest_field = None

                    elif latest_field and latest_field in ('p', 'c', 'd'):
                        if latest_field == 'p':
                            for w in l.split(' '):
                                if w:
                                    word = w.strip()
                                    data['p'].add(word)

                                    word_split = word.split('=')

                                    if word_split[0] != word:
                                        data['p'].add(word_split[0])
                        else:
                            data[latest_field].update((w.strip() for w in l.split(' ') if w))

        return res


def upgrade_several(pkgnames: Iterable[str], root_password: Optional[str], overwrite_conflicting_files: bool = False,
                    skip_dependency_checks: bool = False,
                    conflicting_files: Optional[Collection[str]] = None) -> SimpleProcess:
    cmd = ['pacman', '-S', *pkgnames, '--noconfirm']

    if overwrite_conflicting_files:
        if conflicting_files:
            cmd.extend(f'--overwrite={path}' for path in conflicting_files)
        else:
            cmd.append('--overwrite=*')

    if skip_dependency_checks:
        cmd.append('-dd')

    return SimpleProcess(cmd=cmd,
                         root_password=root_password,
                         error_phrases={'error: failed to prepare transaction', 'error: failed to commit transaction', 'error: target not found'},
                         shell=False)


def download(root_password: Optional[str], *pkgnames: str) -> SimpleProcess:
    return SimpleProcess(cmd=['pacman', '-Swdd', *pkgnames, '--noconfirm', '--noprogressbar'],
                         root_password=root_password,
                         error_phrases={'error: failed to prepare transaction', 'error: failed to commit transaction', 'error: target not found'},
                         shell=False)


def remove_several(pkgnames: Iterable[str], root_password: Optional[str], skip_checks: bool = False) -> SimpleProcess:
    """
    Genera el proceso de desinstalacion.

    El exito se decide por el codigo de retorno y por 'error_phrases', igual que
    install_as_process/upgrade_several. Antes cualquier 'warning:' en la salida (pacman los
    imprime con frecuencia) convertia un fallo en exito y la transaccion continuaba con la
    lista de paquetes eliminados desincronizada.
    """
    cmd = ['pacman', '-R', *pkgnames, '--noconfirm']

    if skip_checks:
        cmd.append('-dd')

    return SimpleProcess(cmd=cmd,
                         root_password=root_password,
                         error_phrases={'error: failed to prepare transaction',
                                        'error: failed to commit transaction',
                                        'error: target not found'},
                         shell=False)


def _map_optional_dep(line: str, not_installed: bool) -> Optional[Tuple[str, Optional[str]]]:
    if not not_installed or not line.endswith('[installed]'):
        pkg_desc = line.split(':')

        if len(pkg_desc) == 1:
            return pkg_desc[0].split('[installed]')[0].strip(), ''
        elif len(pkg_desc) > 1:
            return pkg_desc[0], pkg_desc[1].split('[installed]')[0].strip()


def map_optional_deps(names: Iterable[str], remote: bool, not_installed: bool = False) -> Dict[str, Dict[str, str]]:
    output = _run(['pacman', '-{}i'.format('S' if remote else 'Q'), *names])
    res = {}
    if output:
        latest_name, deps = None, None

        for raw_line in output.split('\n'):
            if raw_line:
                if raw_line[0] != ' ':
                    line = raw_line.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()

                    if field == 'Name':
                        val = line[field_sep_idx + 1:].strip()
                        latest_name = val
                    elif field == 'Optional Deps':
                        val = line[field_sep_idx + 1:].strip()
                        deps = {}
                        if val != 'None':
                            dep_desc = _map_optional_dep(val, not_installed)

                            if dep_desc:
                                deps[dep_desc[0]] = dep_desc[1]

                    elif latest_name and deps is not None:
                        res[latest_name] = deps
                        latest_name, deps = None, None

                elif latest_name and deps is not None:
                    dep_desc = _map_optional_dep(raw_line.strip(), not_installed)

                    if dep_desc:
                        deps[dep_desc[0]] = dep_desc[1]

    return res


def map_required_dependencies(*names: str) -> Dict[str, Set[str]]:
    output = _run(['pacman', '-Qi', *(names if names else ())])

    if output:
        res = {}
        latest_name, deps, latest_field = None, None, None

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()

                    if field == 'Name':
                        val = line[field_sep_idx + 1:].strip()
                        latest_name = val
                        deps = None
                    elif field == 'Depends On':
                        val = line[field_sep_idx + 1:].strip()

                        if deps is None:
                            deps = set()

                        if val != 'None':
                            deps.update((dep for dep in val.split(' ') if dep))

                    elif latest_name and deps is not None:
                        res[latest_name] = deps
                        latest_name, deps, latest_field = None, None, None

                elif latest_name and deps is not None:
                    deps.update((dep for dep in l.split(' ') if dep))

        return res


def get_cache_dir() -> str:
    dir_pattern = re.compile(r'.*CacheDir\s*=\s*.+')

    if os.path.exists('/etc/pacman.conf'):
        with open('/etc/pacman.conf') as f:
            config_str = f.read()

        cache_dirs = []

        for string in dir_pattern.findall(config_str):
            if not string.strip().startswith('#'):
                cache_dirs.append(string.split('=')[1].strip())

        if cache_dirs:
            if cache_dirs[-1][-1] == '/':
                return cache_dirs[-1][0:-1]
            else:
                return cache_dirs[-1]
        else:
            return '/var/cache/pacman/pkg'


def map_required_by(names: Iterable[str] = None, remote: bool = False) -> Dict[str, Set[str]]:
    output = _run(['pacman', f"-{'Sii' if remote else 'Qi'}", *(names if names else ())],
                  print_error=False)

    if output:
        latest_name, required = None, None
        res = {}

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()

                    if field == 'Name':
                        val = line[field_sep_idx + 1:].strip()
                        latest_name = val
                    elif field == 'Required By':
                        val = line[field_sep_idx + 1:].strip()
                        required = set()
                        if val != 'None':
                            required.update((d for d in val.split(' ') if d))

                    elif latest_name and required is not None:
                        res[latest_name] = required
                        latest_name, required = None, None

                elif latest_name and required is not None:
                    required.update(required.update((d for d in l.strip().split(' ') if d)))
        return res
    elif names:
        return {n: set() for n in names}
    else:
        return {}


def map_conflicts_with(names: Iterable[str], remote: bool) -> Dict[str, Dict[str, Set[str]]]:
    output = _run(['pacman', '-{}i'.format('S' if remote else 'Q'), *names])

    if output:
        res = {}
        latest_name, conflicts, replaces, field = None, None, None, None

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()

                    if field == 'Name':
                        field = 'n'
                        val = line[field_sep_idx + 1:].strip()
                        latest_name = val
                    elif field == 'Conflicts With':
                        field = 'c'
                        val = line[field_sep_idx + 1:].strip()
                        conflicts = set()
                        if val != 'None':
                            conflicts.update((d for d in val.split(' ') if d))
                    elif field == 'Replaces':
                        field = 'r'
                        val = line[field_sep_idx + 1:].strip()
                        replaces = set()
                        if val != 'None':
                            replaces.update((d for d in val.split(' ') if d))

                    elif latest_name and conflicts is not None and replaces is not None:
                        field = None
                        res[latest_name] = {'c': conflicts, 'r': replaces}
                        latest_name, conflicts, replaces = None, None, None

                elif latest_name and field:
                    if field == 'c':
                        conflicts.update((d for d in l.strip().split(' ') if d))
                    elif field == 'r':
                        replaces.update((d for d in l.strip().split(' ') if d))

        return res


def map_replaces(names: Iterable[str], remote: bool = False) -> Dict[str, Set[str]]:
    output = _run(['pacman', '-{}i'.format('S' if remote else 'Q'), *names])

    if output:
        res = {}
        latest_name, replaces = None, None

        for l in output.split('\n'):
            if l:
                if l[0] != ' ':
                    line = l.strip()
                    field_sep_idx = line.index(':')
                    field = line[0:field_sep_idx].strip()

                    if field == 'Name':
                        val = line[field_sep_idx + 1:].strip()
                        latest_name = val
                    elif field == 'Replaces':
                        val = line[field_sep_idx + 1:].strip()
                        replaces = set()
                        if val != 'None':
                            replaces.update((d for d in val.split(' ') if d))

                    elif latest_name and replaces is not None:
                        res[latest_name] = replaces
                        latest_name, replaces = None, None

                elif latest_name and replaces is not None:
                    replaces.update((d for d in l.strip().split(' ') if d))

        return res


def list_installed_names() -> Set[str]:
    output = _run(['pacman', '-Qq'], print_error=False)
    return {name.strip() for name in output.split('\n') if name} if output else set()


def list_available_mirrors() -> List[str]:
    _, output = system.run(['pacman-mirrors', '--status', '--no-color'])

    if output:
        mirrors = RE_AVAILABLE_MIRRORS.findall(output)

        if mirrors:
            mirrors.sort(key=lambda o: o[0])
            return [m[1] for m in mirrors]


def get_mirrors_branch() -> str:
    _, output = system.run(['pacman-mirrors', '-G'])
    return output.strip()


def get_packages_to_sync_first() -> Set[str]:
    if os.path.exists('/etc/pacman.conf'):
        with open('/etc/pacman.conf') as f:
            to_sync_first = RE_PACMAN_SYNC_FIRST.findall(f.read())

            if to_sync_first:
                return {s.strip() for s in to_sync_first[0].split(' ') if s and s.strip()}

    return set()


def is_snapd_installed() -> bool:
    return bool(_run(['pacman', '-Qq', 'snapd'], print_error=False))


def list_hard_requirements(name: str, logger: Optional[logging.Logger] = None,
                           assume_installed: Optional[Set[str]] = None) -> Optional[Set[str]]:
    cmd = ['pacman', '-Rc', name, '--print-format=%n']

    if assume_installed:
        cmd.extend(f'--assume-installed={provider}' for provider in assume_installed)

    code, output = _execute(cmd)

    if code != 0:
        if 'HoldPkg' in output:
            raise PackageInHoldException()
        elif 'target not found' in output:
            raise PackageNotFoundException(name)
        elif logger:
            logger.error("Unexpected error while listing hard requirements of: {}".format(name))
            print('{}{}{}'.format(Fore.RED, output, Fore.RESET))
    elif output:
        reqs = set()

        for line in output.split('\n'):
            if line:
                line_strip = line.strip()

                if line_strip and line_strip != name:
                    reqs.add(line_strip)

        return reqs


def list_post_uninstall_unneeded_packages(names: Set[str]) -> Set[str]:
    output = _run(['pacman', '-Rss', *names, '--print-format=%n'], print_error=False)

    reqs = set()
    if output:
        for line in output.split('\n'):
            if line:
                line_strip = line.strip()

                if line_strip and line_strip not in names:
                    reqs.add(line_strip)

    return reqs


def find_one_match(name: str) -> Optional[str]:
    output = _run(['pacman', '-Ssq', name], print_error=False)

    if output:
        matches = [l.strip() for l in output.split('\n') if l.strip()]

        if matches and len(matches) == 1:
            return matches[0]


def map_available_packages() -> Optional[Dict[str, Any]]:
    output = _run(['pacman', '-Sl'])

    if output:
        res = dict()
        for line in output.split('\n'):
            line_strip = line.strip()

            if line_strip:
                package_data = line.split(' ')

                if len(package_data) >= 3:
                    pkgname = package_data[1].strip()

                    if pkgname:
                        res[pkgname] = {'v': package_data[2].strip(),
                                        'r': package_data[0].strip(),
                                        'i': len(package_data) == 4 and 'installed' in package_data[3]}
        return res


def map_installed(pkgs: Optional[Collection[str]] = None) -> Optional[Dict[str, str]]:
    output = _run(['pacman', '-Q', *(sorted({*pkgs}) if pkgs else ())], print_error=False)

    if output:
        res = dict()
        for raw_line in output.split("\n"):
            line = raw_line.strip()

            if line:
                pkg_version = line.split(" ")
                if len(pkg_version) == 2:
                    res[pkg_version[0]] = pkg_version[1]
        return res
