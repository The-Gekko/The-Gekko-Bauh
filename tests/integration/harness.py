"""Utilidades para ejecutar las gems contra binarios simulados en el PATH.

Las gems no hablan con la API de pacman, eopkg o flatpak: lanzan sus ejecutables y analizan
la salida. Los tests unitarios parchean esa frontera, de modo que un cambio en los argumentos
o en el análisis de la salida no rompe nada aunque el comando real quede mal construido.

Aquí se sustituye el binario, no la función: se crea un script en un directorio temporal que
se antepone al ``PATH``, se le da la salida que debe imprimir y se guarda cada invocación con
sus argumentos. Así se comprueba a la vez lo que la gem *ejecuta* y lo que *entiende*.
"""

import json
import os
import stat
import tempfile
from typing import Dict, List, Optional

# Script que hace de binario falso: registra su invocación y responde según un fichero de
# respuestas indexado por el primer argumento (el subcomando).
FAKE_BINARY_TEMPLATE = """#!/usr/bin/env python3
import json
import os
import sys

BASE = {base!r}
NAME = {name!r}

with open(os.path.join(BASE, 'calls.jsonl'), 'a') as f:
    f.write(json.dumps({{'binary': NAME, 'args': sys.argv[1:]}}) + '\\n')

with open(os.path.join(BASE, 'responses.json')) as f:
    responses = json.load(f)

key = None
for arg in sys.argv[1:]:
    if not arg.startswith('-'):
        key = arg
        break

reply = responses.get(NAME, {{}}).get(key or '', responses.get(NAME, {{}}).get('*'))

if reply is None:
    sys.exit(0)

sys.stdout.write(reply.get('stdout', ''))
sys.stderr.write(reply.get('stderr', ''))
sys.exit(reply.get('code', 0))
"""


class FakeBinaries:
    """Directorio temporal con binarios simulados antepuesto al ``PATH``.

    Uso::

        with FakeBinaries({'eopkg': {'li': {'stdout': 'vlc - VLC\\n'}}}) as fakes:
            ...                       # el código bajo prueba ejecuta 'eopkg li'
            fakes.assert_called('eopkg', ['li', '--no-color'])
    """

    def __init__(self, responses: Dict[str, Dict[str, dict]]):
        self._responses = responses
        self._dir: Optional[tempfile.TemporaryDirectory] = None
        self._old_path: Optional[str] = None

    @property
    def path(self) -> str:
        return self._dir.name

    def __enter__(self) -> 'FakeBinaries':
        # `bauh.commons.system` fotografía el PATH al importarse (`PATH = os.getenv('PATH')`)
        # y `gen_env()` reparte esa copia a todos los subprocesos, así que cambiar
        # `os.environ['PATH']` no basta: hay que sustituir también la constante del módulo.
        from bauh.commons import system as bauh_system

        self._system = bauh_system
        self._old_module_paths = (bauh_system.PATH, bauh_system.GLOBAL_INTERPRETER_PATH)

        self._dir = tempfile.TemporaryDirectory()

        with open(os.path.join(self.path, 'responses.json'), 'w') as f:
            json.dump(self._responses, f)

        open(os.path.join(self.path, 'calls.jsonl'), 'w').close()

        for name in self._responses:
            script = os.path.join(self.path, name)

            with open(script, 'w') as f:
                f.write(FAKE_BINARY_TEMPLATE.format(base=self.path, name=name))

            os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        self._old_path = os.environ.get('PATH', '')
        new_path = f'{self.path}{os.pathsep}{self._old_path}'
        os.environ['PATH'] = new_path
        self._system.PATH = new_path
        self._system.GLOBAL_INTERPRETER_PATH = new_path
        return self

    def __exit__(self, *_):
        os.environ['PATH'] = self._old_path
        self._system.PATH, self._system.GLOBAL_INTERPRETER_PATH = self._old_module_paths
        self._dir.cleanup()

    def calls(self, binary: Optional[str] = None) -> List[List[str]]:
        """Argumentos de cada invocación, en orden."""
        result = []

        with open(os.path.join(self.path, 'calls.jsonl')) as f:
            for line in f:
                if not line.strip():
                    continue

                call = json.loads(line)

                if binary is None or call['binary'] == binary:
                    result.append(call['args'])

        return result

    def was_called_with(self, binary: str, args: List[str]) -> bool:
        return args in self.calls(binary)
