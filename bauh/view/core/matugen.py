"""Integración con matugen: declara la plantilla de colores de bauh en su configuración.

matugen genera, a partir del fondo de pantalla, los ficheros que cada aplicación
declara como plantilla en ~/.config/matugen/config.toml. Con la de bauh registrada,
en cada cambio de fondo matugen escribe MATUGEN_BAUH_COLORS_FILE y el vigilante de
temas (bauh.context.ThemeWatcher) repinta la ventana sin que haya que hacer nada.

Nunca se reescribe la configuración del usuario: solo se añade una sección al final,
después de guardar una copia, y si el resultado no es TOML válido no se escribe.
"""
import os
import re
import shutil
import time
from typing import Optional, Tuple

from bauh.stylesheet import MATUGEN_BAUH_COLORS_FILE
from bauh.view.util import resource

TEMPLATE_NAME = 'gekko-bauh'
CONFIG_FILE = '~/.config/matugen/config.toml'
TEMPLATE_FILE = f'~/.config/matugen/templates/{TEMPLATE_NAME}.css'
BUNDLED_TEMPLATE = 'style/matugen/gekko-bauh-colors.css'

# la sección de bauh, como tabla ([templates.gekko-bauh]) o como entrada en línea
# dentro de [templates] (gekko-bauh = { ... }), con o sin comillas en el nombre
RE_REGISTERED = re.compile(r'^\s*(\[\s*templates\s*\.\s*["\']?gekko-bauh["\']?\s*]|["\']?gekko-bauh["\']?\s*=)',
                           re.MULTILINE)


def is_installed() -> bool:
    return bool(shutil.which('matugen'))


def bundled_template_path() -> str:
    return resource.get_path(BUNDLED_TEMPLATE)


def is_registered(config_file: str = CONFIG_FILE) -> bool:
    path = os.path.expanduser(config_file)

    if not os.path.isfile(path):
        return False

    with open(path, encoding='utf-8') as f:
        return bool(RE_REGISTERED.search(f.read()))


def template_entry(template_file: str = TEMPLATE_FILE, output_file: str = MATUGEN_BAUH_COLORS_FILE) -> str:
    # comillas simples: en TOML son cadenas literales, así que '~' y las barras llegan tal cual
    return ('# Añadido por bauh Gekko Edition: colores de la tienda a partir del fondo de pantalla.\n'
            f'[templates.{TEMPLATE_NAME}]\n'
            f"input_path = '{template_file}'\n"
            f"output_path = '{output_file}'\n")


def _toml_error(content: str) -> Optional[str]:
    """El error de sintaxis del TOML, o None si es válido o no se puede comprobar (Python < 3.11)."""
    try:
        import tomllib
    except ImportError:
        return None

    try:
        tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        return str(e)

    return None


def register(config_file: str = CONFIG_FILE, template_file: str = TEMPLATE_FILE,
             output_file: str = MATUGEN_BAUH_COLORS_FILE) -> Tuple[bool, Optional[str]]:
    """Instala la plantilla y la declara en la configuración de matugen.

    Devuelve (True, ruta de la copia de seguridad o None) si quedó registrada, o
    (False, motivo) si no se tocó la configuración.
    """
    config_path = os.path.expanduser(config_file)
    template_path = os.path.expanduser(template_file)

    try:
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        shutil.copyfile(bundled_template_path(), template_path)
    except OSError as e:
        return False, str(e)

    if is_registered(config_file):
        return True, None

    original = None

    if os.path.isfile(config_path):
        with open(config_path, encoding='utf-8') as f:
            original = f.read()

    if original is None:
        content = '[config]\n\n' + template_entry(template_file, output_file)
    else:
        content = original.rstrip('\n') + '\n\n' + template_entry(template_file, output_file)

    error = _toml_error(content)

    if error:
        return False, error

    backup = None

    try:
        if original is not None:
            backup = f'{config_path}.bak-gekko-bauh-{time.strftime("%Y%m%d%H%M%S")}'
            shutil.copy2(config_path, backup)
        else:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except OSError as e:
        return False, str(e)

    return True, backup
