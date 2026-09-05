"""Analizadores tolerantes para la salida de la herramienta ``eopkg`` de Solus.

Suposiciones documentadas (basadas en la especificación aportada por el dueño del fork):

* Todos los comandos se ejecutan con ``--no-color`` (equivale a ``-N``: sólo suprime el
  coloreado ANSI, NO desactiva los prompts interactivos; el modificador no interactivo es
  ``-y`` / ``--yes-all``).  Aun así los analizadores eliminan secuencias ANSI por si el
  binario ignorase el modificador.
* La salida de ``eopkg`` está traducida al idioma del sistema.  El controlador fuerza
  ``LANG``/``LC_ALL`` a la locale C para obtener los textos en inglés, pero los
  analizadores reconocen además las variantes en español que aparecen en la
  especificación, de modo que un entorno mal configurado degrade con elegancia.
* ``eopkg search``/``list-installed``/``list-upgrades`` emiten una línea por paquete con el
  formato clásico de pisi ``"nombre - resumen"``.  Con ``--install-info`` la salida pasa a
  ser una tabla separada por ``|`` (``Nombre |St| Versión | Rel. | Distro | Fecha``).
  También se admite una tabla separada por espacios ``nombre versión release resumen``.
* Las líneas informativas (``No packages to upgrade.``, ``Failed to record path /lib32``,
  las marcas de progreso ``[✓] ...``) NO son paquetes ni errores y se descartan.
"""

import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

# secuencias de escape ANSI (por si el binario ignorase --no-color)
RE_ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# un nombre de paquete de Solus: letras, dígitos y los separadores + . _ -
RE_PKG_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9+._-]*$')

# una versión siempre empieza por dígito ("3.0.20", "1.0.155", "2:1.4-1")
RE_VERSION = re.compile(r'^\d[\w.+~:-]*$')

# "Installed 1 / 4" / "Instalado 1 / 4"
RE_PROGRESS = re.compile(r'^(?:installed|instalado[s]?)\s+(\d+)\s*/\s*(\d+)\s*$', re.IGNORECASE)

# "Installing discord, version 1.0.155, release 176" / "Instalando discord, versión ..."
RE_INSTALLING = re.compile(
    r'^(?:installing|instalando)\s+(?P<name>[A-Za-z0-9][A-Za-z0-9+._-]*)\s*,\s*'
    r'(?:version|versi[oó]n)\s*:?\s*(?P<version>[^\s,]+)\s*,\s*'
    r'(?:release|lanzamiento|revisi[oó]n)\s*:?\s*(?P<release>\S+)\s*$',
    re.IGNORECASE)

# "Installed discord" / "Instalado discord" (nunca "Installed 1 / 4")
RE_INSTALLED_PKG = re.compile(
    r'^(?:installed|instalado)\s+(?P<name>[A-Za-z0-9][A-Za-z0-9+._-]*)\s*$', re.IGNORECASE)

# "Removed discord" / "Removido discord" (nunca "Removing package discord")
RE_REMOVED_PKG = re.compile(
    r'^(?:removed|removid[oa]|eliminad[oa])\s+(?P<name>[A-Za-z0-9][A-Za-z0-9+._-]*)\s*$',
    re.IGNORECASE)

# cabecera del listado de paquetes que se van a eliminar
RE_REMOVAL_HEADER = re.compile(
    r'(will be removed|ser[aá]n? (?:removid|eliminad)|lista de paquetes)', re.IGNORECASE)

# cabecera del listado de paquetes que se van a instalar
RE_INSTALL_HEADER = re.compile(
    r'(will be installed|ser[aá]n? instalad|se instalar)', re.IGNORECASE)

# "Do you want to continue ? (yes/no)" / "Desea continuar ? (yes/no)"
RE_CONTINUE_PROMPT = re.compile(r'(want to continue|desea continuar)', re.IGNORECASE)

# "No packages to upgrade." y su equivalente traducido
RE_NO_UPGRADES = re.compile(
    r'(no packages? to upgrade|no hay paquetes (?:que|para) actualizar)', re.IGNORECASE)

# línea compuesta de 'eopkg info': "Name : vlc, version: 3.0.20, release: 78"
# El release se acota con [^\s:]+ y no con \S+: eopkg envuelve esta línea (ver
# _merge_wrapped_name_lines) y puede dejarla cortada justo detrás de 'release:', y con \S+
# ese resto casaba con release=':', dando por buena media línea.  Tampoco se usa \d+ aunque
# el release de eopkg sea siempre un entero: el módulo prefiere ser tolerante con formatos
# ajenos, y excluir los dos puentes (espacio y dos puntos) ya basta para el corte.
RE_INFO_NAME_LINE = re.compile(
    r'^(?:name|nombre)\s*:\s*(?P<name>[^\s,]+)\s*,\s*'
    r'(?:version|versi[oó]n)\s*:?\s*(?P<version>[^\s,]+)\s*,\s*'
    r'(?:release|lanzamiento|revisi[oó]n)\s*:?\s*(?P<release>[^\s:]+)\s*$',
    re.IGNORECASE)

# inicio de la línea compuesta, que eopkg parte en dos cuando el nombre es largo
RE_INFO_NAME_START = re.compile(r'^(?:name|nombre)\s*:', re.IGNORECASE)

# final de una línea compuesta cortada: eopkg parte por el último espacio, y ahí sólo hay
# espacios detrás de una coma o de 'version:'/'release:'
RE_INFO_NAME_CUT = re.compile(r'[,:]$')

RE_INFO_FIELD = re.compile(r'^(?P<key>[^:]{1,60}?)\s*:\s*(?P<value>.*)$')
RE_INFO_BLOCK_HEADER = re.compile(r'^(?P<title>[^:]{1,80}):\s*$')

# líneas de ruido conocidas: no son paquetes ni errores
RE_NOISE = (
    re.compile(r'^failed to record path\b', re.IGNORECASE),
    re.compile(r'^\s*\[[^\]]{1,4}\]\s'),               # " [✓] Syncing filesystems   success"
    re.compile(r'^(?:downloading|downloaded|descargando|descargado)\b', re.IGNORECASE),
    re.compile(r'^(?:finished downloading|extracting the files|extrayendo)\b', re.IGNORECASE),
    re.compile(r'^(?:disabling keyboard interrupts|total (?:size|installed size)|'
               r'tama[ñn]o total)\b', re.IGNORECASE),
    re.compile(r'^(?:there are extra packages|hay paquetes adicionales)\b', re.IGNORECASE),
    re.compile(r'^(?:updating repository|actualizando repositorio)\b', re.IGNORECASE),
)

# equivalencias de las claves de 'eopkg info' a nombres canónicos internos
KEY_ALIASES = {
    'name': 'name', 'nombre': 'name',
    'summary': 'summary', 'resumen': 'summary',
    'description': 'description', 'descripcion': 'description', 'descripción': 'description',
    'license': 'licenses', 'licenses': 'licenses',
    'licencia': 'licenses', 'licencias': 'licenses',
    'component': 'component', 'componente': 'component',
    'dependencies': 'dependencies', 'dependencias': 'dependencies',
    'reverse dependencies': 'reverse_dependencies',
    'distribution': 'distribution', 'distribucion': 'distribution', 'distribución': 'distribution',
    'installed size': 'installed_size',
    'tamano instalado': 'installed_size', 'tamaño instalado': 'installed_size',
    'package size': 'package_size',
    'tamano del paquete': 'package_size', 'tamaño del paquete': 'package_size',
    'size': 'size', 'tamano': 'size', 'tamaño': 'size',
    'version': 'version', 'versión': 'version',
    'release': 'release', 'lanzamiento': 'release',
    'distro release': 'distro_release',
    'installed time': 'installed_time',
    'homepage': 'homepage',
}

# claves reconocidas aunque la línea venga indentada
KNOWN_FIELD_KEYS = frozenset(KEY_ALIASES.values())


def strip_ansi(text: Optional[str]) -> str:
    """Elimina las secuencias de escape ANSI de un texto."""
    if not text:
        return ''
    return RE_ANSI.sub('', text)


def is_noise_line(line: str) -> bool:
    """Indica si una línea es ruido informativo de eopkg (no un paquete ni un error)."""
    if not line:
        return True

    return any(pattern.search(line) for pattern in RE_NOISE)


def _iter_content_lines(output: Optional[str]) -> Iterator[str]:
    """Itera sobre las líneas útiles de una salida: sin ANSI, sin vacías y sin ruido."""
    for raw in strip_ansi(output).splitlines():
        line = raw.strip()

        if not line or is_noise_line(line):
            continue

        yield line


def normalize_key(key: str) -> str:
    """Normaliza la clave de un campo de 'eopkg info' a su nombre canónico interno."""
    normalized = re.sub(r'\s+', ' ', key.strip().lower())
    return KEY_ALIASES.get(normalized, normalized.replace(' ', '_'))


def format_version(version: Optional[str], release: Optional[str] = None) -> Optional[str]:
    """Compone la cadena de versión mostrada al usuario ('3.0.20-78')."""
    if not version:
        return None

    return f'{version}-{release}' if release else version


def _split_table_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Analiza una línea de tabla separada por '|' ('nombre |St| versión | rel | ...')."""
    fields = [field.strip() for field in line.split('|')]
    name = fields[0]

    if not RE_PKG_NAME.match(name):
        return None

    version, release = None, None
    rest = fields[1:]

    for idx, field in enumerate(rest):
        if RE_VERSION.match(field):
            version = field

            if idx + 1 < len(rest) and rest[idx + 1].isdigit():
                release = rest[idx + 1]

            break

    return {'name': name, 'version': version, 'release': release, 'summary': ''}


def parse_package_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Analiza una línea de listado de paquetes en cualquiera de los formatos conocidos.

    Devuelve un diccionario con 'name', 'version', 'release' y 'summary', o ``None`` si la
    línea no describe un paquete (cabeceras, mensajes informativos, etc.).
    """
    if not line or line.endswith(':'):
        return None

    # Las estrategias se prueban en cascada y ninguna aborta el análisis: un resumen que
    # contenga « - » o «|» («ranger - Console file manager | vim-like») haría fracasar a la
    # especializada, y devolver None ahí borraba el paquete del listado en silencio.
    if '|' in line:
        entry = _split_table_line(line)

        if entry:
            return entry

    entry = _split_columns_line(line)

    if entry:
        return entry

    if ' - ' in line:
        name, summary = line.split(' - ', 1)
        name = name.strip()

        if RE_PKG_NAME.match(name):
            return {'name': name, 'version': None, 'release': None, 'summary': summary.strip()}

    return None


def _split_columns_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Analiza una línea de tabla separada por espacios ('nombre versión release resumen')."""
    parts = line.split()

    if not parts or not RE_PKG_NAME.match(parts[0]):
        return None

    if len(parts) == 1:
        return {'name': parts[0], 'version': None, 'release': None, 'summary': ''}

    # sólo se acepta si el segundo campo parece una versión. Así se descartan frases
    # informativas del tipo "No packages to upgrade."
    if not RE_VERSION.match(parts[1]):
        return None

    release, summary_idx = None, 2

    if len(parts) > 2 and parts[2].isdigit():
        release, summary_idx = parts[2], 3

    return {'name': parts[0], 'version': parts[1], 'release': release,
            'summary': ' '.join(parts[summary_idx:]).strip()}


def parse_search(output: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """Analiza la salida de ``eopkg sr`` ('nombre - resumen' por línea)."""
    return parse_package_list(output)


def parse_package_list(output: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """Analiza un listado de paquetes (``sr``, ``li``, ``la``) sin duplicados."""
    packages, seen = [], set()

    for line in _iter_content_lines(output):
        entry = parse_package_line(line)

        if entry and entry['name'] not in seen:
            seen.add(entry['name'])
            packages.append(entry)

    return packages


def parse_upgradable(output: Optional[str]) -> List[str]:
    """Devuelve los nombres de ``eopkg list-upgrades``.

    Ignora explícitamente el mensaje «No packages to upgrade.» (y su traducción), que en la
    implementación anterior producía una actualización fantasma llamada «No».
    """
    names, seen = [], set()

    for line in _iter_content_lines(output):
        if RE_NO_UPGRADES.search(line):
            continue

        entry = parse_package_line(line)

        if entry and entry['name'] not in seen:
            seen.add(entry['name'])
            names.append(entry['name'])

    return names


def parse_upgradable_entries(output: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """Como :func:`parse_upgradable` pero conservando versión y release si están presentes."""
    entries, seen = [], set()

    for line in _iter_content_lines(output):
        if RE_NO_UPGRADES.search(line):
            continue

        entry = parse_package_line(line)

        if entry and entry['name'] not in seen:
            seen.add(entry['name'])
            entries.append(entry)

    return entries


def _merge_wrapped_name_lines(lines: List[str]) -> List[str]:
    """Rejunta la línea compuesta de ``eopkg info`` cuando el nombre del paquete la parte.

    eopkg envuelve ``Name : x, version: v, release: n`` si el nombre es largo (por ejemplo
    ``nvidia-580-glx-driver-common``) y deja el resto en una línea indentada aparte.  Sin
    rejuntarlas, :data:`RE_INFO_NAME_LINE` no casaba y el bloque acababa identificado por el
    texto entero (``'nvidia-...-common, version: 580.178.04,'``) y sin versión: la lista de
    actualizaciones mostraba esos paquetes sin número de versión y ``get_info`` no los
    encontraba.

    El corte no cae siempre detrás de la coma.  ``align()`` (``pisi/cli/__init__.py``)
    retrocede hasta el último espacio anterior a la columna ``ancho - 22`` (58 con el ancho
    de reserva de 80 columnas), y en esta línea los únicos espacios van detrás de una coma o
    detrás de ``version:`` / ``release:``.  Barriendo el índice real de Solus con ese
    algoritmo, de los 325 paquetes cuya línea se envuelve, 167 cortan tras la coma
    (``anoise-media-community-extension1``), 153 tras ``release:``
    (``abseil-cpp-32bit-dbginfo``) y 5 tras ``version:``
    (``gnome-shell-extension-native-window-placement``): por eso se admiten los dos finales.
    """
    merged: List[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if (RE_INFO_NAME_START.match(stripped) and not RE_INFO_NAME_LINE.match(stripped)
                and RE_INFO_NAME_CUT.search(stripped)):
            joined = stripped

            # sólo se absorben continuaciones indentadas, y sólo hasta completar la línea:
            # los campos siguientes ('Summary', 'Licenses'...) empiezan en la columna cero
            while idx + 1 < len(lines) and lines[idx + 1][:1].isspace():
                joined = f'{joined} {lines[idx + 1].strip()}'
                idx += 1

                if RE_INFO_NAME_LINE.match(joined):
                    break

            line = joined

        merged.append(line)
        idx += 1

    return merged


def _classify_section(title: str) -> Optional[str]:
    """Clasifica la cabecera de un bloque de 'eopkg info'."""
    lowered = title.strip().lower()

    if 'repositor' in lowered:
        return 'repository'

    if 'install' in lowered or 'instalad' in lowered:
        return 'installed'

    return None


def parse_info_blocks(output: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """Analiza la salida de ``eopkg info`` y devuelve un bloque por paquete encontrado.

    Cada bloque es un diccionario con 'section' ('installed', 'repository' o ``None``),
    'name', 'version', 'release' y el resto de campos normalizados
    (summary, description, licenses, component, dependencies, installed_size...).
    """
    blocks: List[Dict[str, Optional[str]]] = []
    current: Optional[Dict[str, Optional[str]]] = None
    pending_section: Optional[str] = None
    last_key: Optional[str] = None

    def start_block(name: Optional[str], version: Optional[str], release: Optional[str]):
        nonlocal current, pending_section, last_key
        current = {'section': pending_section, 'name': name, 'version': version,
                   'release': release}
        blocks.append(current)
        pending_section = None
        last_key = 'name'

    for raw in _merge_wrapped_name_lines(strip_ansi(output).splitlines()):
        line = raw.strip()

        if not line or is_noise_line(line):
            continue

        name_match = RE_INFO_NAME_LINE.match(line)

        if name_match:
            start_block(name_match.group('name'), name_match.group('version'),
                        name_match.group('release'))
            continue

        header_match = RE_INFO_BLOCK_HEADER.match(line)

        if header_match:
            pending_section = _classify_section(header_match.group('title'))
            continue

        field_match = RE_INFO_FIELD.match(line)
        indented = raw[:1].isspace()

        if field_match:
            key = normalize_key(field_match.group('key'))
            value = field_match.group('value').strip()

            if not indented or key in KNOWN_FIELD_KEYS:
                if key == 'name':
                    start_block(value or None, None, None)
                    continue

                if current is not None:
                    current[key] = value
                    last_key = key

                continue

        if current is not None and last_key and indented:
            previous = current.get(last_key) or ''
            current[last_key] = f'{previous} {line}'.strip()

    return blocks


def index_info_blocks(blocks: Iterable[Dict[str, Optional[str]]]) -> Dict[str, Dict[str, dict]]:
    """Indexa los bloques de 'eopkg info' por nombre de paquete y sección."""
    index: Dict[str, Dict[str, dict]] = {}

    for block in blocks:
        name = block.get('name')

        if not name:
            continue

        sections = index.setdefault(name, {})
        section = block.get('section')

        if not section:
            section = 'installed' if 'installed' not in sections else 'repository'

        sections.setdefault(section, block)

    return index


def parse_install_progress(line: str) -> Optional[Tuple[int, int]]:
    """Devuelve (actual, total) de una línea «Installed N / M», o ``None``."""
    match = RE_PROGRESS.match(strip_ansi(line).strip())

    if not match:
        return None

    return int(match.group(1)), int(match.group(2))


def parse_installing_package(line: str) -> Optional[Dict[str, str]]:
    """Analiza «Installing X, version Y, release Z» devolviendo sus componentes."""
    match = RE_INSTALLING.match(strip_ansi(line).strip())

    if not match:
        return None

    return {'name': match.group('name'), 'version': match.group('version'),
            'release': match.group('release')}


class TransactionTargetsCollector:
    """Reconstruye, línea a línea, la lista de paquetes que eopkg anuncia antes de actuar.

    eopkg imprime una cabecera («The following list of packages will be removed…»), a
    continuación la lista de nombres y por último la pregunta de confirmación.  Como el
    proceso se ejecuta con ``-y`` la pregunta se autorresponde, pero la lista sigue estando
    en la salida y es la que debe verse en el ProcessWatcher.
    """

    def __init__(self, header: 're.Pattern' = RE_REMOVAL_HEADER):
        self._header = header
        self._in_list = False
        self._completed = False
        self.targets: List[str] = []

    @property
    def completed(self) -> bool:
        return self._completed

    def feed(self, line: str) -> bool:
        """Procesa una línea. Devuelve ``True`` si la lista acaba de completarse."""
        if self._completed:
            return False

        text = strip_ansi(line).strip()

        if not text:
            return False

        if not self._in_list:
            if self._header.search(text):
                self._in_list = True

            return False

        if RE_CONTINUE_PROMPT.search(text) or is_noise_line(text):
            self._completed = bool(self.targets)
            return self._completed

        tokens = text.split()

        if tokens and all(RE_PKG_NAME.match(token) for token in tokens):
            for token in tokens:
                if token not in self.targets:
                    self.targets.append(token)

            return False

        # continuación de la cabecera ("en el orden indicado, para satisfacer ... :")
        if text.endswith((':', ',')):
            return False

        self._completed = bool(self.targets)
        return self._completed

    def feed_all(self, output: Optional[str]) -> List[str]:
        for raw in strip_ansi(output).splitlines():
            self.feed(raw)

        return self.targets


def _parse_transaction_targets(output: Optional[str], header: 're.Pattern') -> List[str]:
    """Extrae la lista de paquetes que eopkg anuncia antes de pedir confirmación."""
    return TransactionTargetsCollector(header).feed_all(output)


def parse_removal_targets(output: Optional[str]) -> List[str]:
    """Paquetes que ``eopkg rmf`` anuncia que va a eliminar (el paquete y sus huérfanos)."""
    return _parse_transaction_targets(output, RE_REMOVAL_HEADER)


def parse_install_targets(output: Optional[str]) -> List[str]:
    """Paquetes que ``eopkg it`` anuncia que va a instalar (incluidas las dependencias)."""
    return _parse_transaction_targets(output, RE_INSTALL_HEADER)


def parse_removed_packages(output: Optional[str]) -> List[str]:
    """Paquetes efectivamente eliminados según las líneas «Removed X»."""
    removed, seen = [], set()

    for raw in strip_ansi(output).splitlines():
        match = RE_REMOVED_PKG.match(raw.strip())

        if match:
            name = match.group('name')

            if name not in seen:
                seen.add(name)
                removed.append(name)

    return removed


def parse_installed_packages(output: Optional[str]) -> List[str]:
    """Paquetes efectivamente instalados según las líneas «Installed X»."""
    installed, seen = [], set()

    for raw in strip_ansi(output).splitlines():
        match = RE_INSTALLED_PKG.match(raw.strip())

        if match:
            name = match.group('name')

            if name not in seen:
                seen.add(name)
                installed.append(name)

    return installed
