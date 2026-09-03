import logging
import re
from abc import ABC
from datetime import datetime, timezone
from logging import Logger
from typing import Optional, Union

# metacaracteres de la shell que se eliminan de una entrada de usuario antes de usarla en un comando
# (incluye ` ( ) para neutralizar sustituciones de comandos como $(...) o `...`)
re_command_forbidden_symbols = re.compile(r'[\'\"%$#*<>`()]')
re_several_spaces = re.compile(r'\s+')
re_command_parameter = re.compile(r'(^|\s)-+\w+')


class NullLoggerFactory(ABC):

    __instance: Optional[Logger] = None

    @classmethod
    def logger(cls) -> Logger:
        if cls.__instance is None:
            cls.__instance = logging.getLogger('__null__')
            cls.__instance.addHandler(logging.NullHandler())

        return cls.__instance


def deep_update(source: dict, overrides: dict):
    for key, value in overrides.items():
        if isinstance(value, dict):
            returned = deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source


def size_to_byte(size: Union[float, int, str], unit: str, logger: Optional[Logger] = None) -> Optional[float]:
    lower_unit = unit.strip().lower()

    if isinstance(size, str):
        try:
            final_size = float(size.strip().replace(',', '.').replace(' ', ''))
        except ValueError:
            if logger:
                logger.error(f"Could not parse string size {size} to bytes")
            return
    else:
        final_size = float(size)

    if unit == 'b':
        return final_size / 8

    if unit == 'B':
        return final_size

    base = 1024 if lower_unit.endswith('ib') else 1000

    if lower_unit[0] == 'k':
        return final_size * base
    elif lower_unit[0] == 'm':
        return final_size * (base ** 2)
    elif lower_unit[0] == 'g':
        return final_size * (base ** 3)
    elif lower_unit[0] == 't':
        return final_size * (base ** 4)
    else:
        return final_size * (base ** 5)


def datetime_as_milis(date: datetime = None) -> int:
    if date is None:
        date = datetime.now(timezone.utc)

    return int(round(date.timestamp() * 1000))


def map_timestamp_file(file_path: str) -> str:
    path_split = file_path.split('/')
    return '/'.join(path_split[0:-1]) + '/' + path_split[-1].split('.')[0] + '.ts'


# operadores que separan comandos en la shell: la entrada se corta en el primero que aparezca
command_separators = ('|', '&', ';', '\n', '\r')


def sanitize_command_input(input_: str) -> str:
    """Sanea una entrada de usuario destinada a formar parte de una línea de comandos:
    corta en el primer separador de comandos (| & ; salto de línea), elimina los metacaracteres de la
    shell (comillas, $ # % * < > ` ( )) y los parámetros con guion, y normaliza los espacios."""
    final_input = input_

    for op in command_separators:
        final_input = final_input.split(op)[0]

    for remove_re in (re_command_forbidden_symbols, re_command_parameter):
        final_input = remove_re.sub('', final_input)

    final_input = re_several_spaces.sub(' ', final_input)
    return final_input.strip()
