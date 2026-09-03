import inspect
import os
import importlib.util
import sys
from logging import Logger
from typing import List, Generator

from bauh import __app_name__, ROOT_DIR
from bauh.api.abstract.controller import SoftwareManager, ApplicationContext
from bauh.view.util import translation

# Politica del administrador del equipo. Se leen las dos rutas y se unen las listas: la heredada
# es literal a proposito, para respetar una prohibicion que el sistema ya tuviera puesta antes de
# instalar este proyecto, y la propia permite configurarlo con el nombre nuevo. Por eso la ruta
# heredada NO se deriva de __app_name__.
LEGACY_FORBIDDEN_GEMS_FILE = '/etc/bauh/gems.forbidden'
FORBIDDEN_GEMS_FILE = f'/etc/{__app_name__}/gems.forbidden'
FORBIDDEN_GEMS_FILES = (LEGACY_FORBIDDEN_GEMS_FILE, FORBIDDEN_GEMS_FILE)


def find_manager(member):
    if not isinstance(member, str):
        if inspect.isclass(member) and issubclass(member, SoftwareManager) and member is not SoftwareManager:
            return member
        elif inspect.ismodule(member):
            for name, mod in inspect.getmembers(member):
                manager_found = find_manager(mod)
                if manager_found:
                    return manager_found


def read_forbidden_gems() -> Generator[str, None, None]:
    for file_path in FORBIDDEN_GEMS_FILES:
        try:
            with open(file_path) as f:
                forbidden_lines = f.readlines()
        except FileNotFoundError:
            continue

        for line in forbidden_lines:
            clean_line = line.strip()

            if clean_line and not clean_line.startswith('#'):
                yield clean_line


def load_managers(locale: str, context: ApplicationContext, config: dict, default_locale: str, logger: Logger) -> List[SoftwareManager]:
    managers = []

    forbidden_gems = {gem for gem in read_forbidden_gems()}

    for f in os.scandir(f'{ROOT_DIR}/gems'):
        if f.is_dir() and f.name != '__pycache__':

            if f.name in forbidden_gems:
                logger.warning(f"gem '{f.name}' could not be loaded because it was marked as forbidden in '{FORBIDDEN_GEMS_FILE}'")
                continue

            spec = importlib.util.find_spec(f'bauh.gems.{f.name}.controller')
            if spec and spec.loader:
                module = sys.modules.get(spec.name)

                if module is None:
                    module = importlib.util.module_from_spec(spec)
                    # Se registra antes de ejecutarlo (como hace el import normal) para que cualquier
                    # 'import bauh.gems.<gem>.controller' posterior reutilice esta misma copia del módulo.
                    sys.modules[spec.name] = module

                    try:
                        spec.loader.exec_module(module)
                    except Exception:
                        sys.modules.pop(spec.name, None)
                        logger.exception(f"gem '{f.name}' could not be loaded")
                        continue

                manager_class = find_manager(module)

                if manager_class:
                    if locale:
                        locale_path = f'{f.path}/resources/locale'

                        if os.path.exists(locale_path):
                            context.i18n.current.update(translation.get_locale_keys(locale, locale_path)[1])

                            if default_locale and context.i18n.default:
                                context.i18n.default.update(translation.get_locale_keys(default_locale, locale_path)[1])

                    man = manager_class(context=context)

                    if config['gems'] is None:
                        man.set_enabled(man.is_default_enabled())
                    else:
                        man.set_enabled(f.name in config['gems'])

                    managers.append(man)

    return managers
