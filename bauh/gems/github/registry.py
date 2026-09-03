"""Registro de lo que la gem ha instalado fuera del clon, y análisis de la salida de build.

Sin este registro «desinstalar» sólo borraría el clon y dejaría en el sistema el paquete de
pacman, la aplicación de pipx o el binario de cargo que la construcción instaló.
"""

import json
import os
import re
import traceback
from typing import Dict, Iterable, List, Optional

from bauh.gems.github import INSTALLED_FILE

# 'ripgrep-13.0.0-1-x86_64.pkg.tar.zst' -> 'ripgrep'
RE_PACMAN_PKG_FILE = re.compile(
    r'^(?P<name>.+)-[^-]+-[^-]+-[^-]+\.pkg\.tar(?:\.[A-Za-z0-9]+)?$')

# pipx: "installed package black 23.1.0, installed using Python 3.11"
RE_PIPX_INSTALLED = re.compile(r'installed package\s+(?P<name>[A-Za-z0-9._-]+)', re.IGNORECASE)

# cargo: "  Installed package `ripgrep v13.0.0` (executables `rg`)"
RE_CARGO_INSTALLED = re.compile(
    r'Installed package\s+[`\'"]?(?P<name>[A-Za-z0-9._+-]+)\s+v', re.IGNORECASE)

# cargo: "  Installing ripgrep v13.0.0 (/home/user/repos/ripgrep)"
RE_CARGO_INSTALLING = re.compile(
    r'^\s*Installing\s+(?P<name>[A-Za-z0-9._+-]+)\s+v', re.IGNORECASE)

# Cargo.toml: name = "ripgrep" dentro de la sección [package]
RE_CARGO_SECTION = re.compile(r'^\s*\[(?P<section>[^\]]+)\]\s*$')
RE_CARGO_NAME = re.compile(r'^\s*name\s*=\s*[\'"](?P<name>[^\'"]+)[\'"]')


def parse_pacman_package_name(file_name: str) -> Optional[str]:
    """Extrae el nombre del paquete de un fichero '<nombre>-<ver>-<rel>-<arch>.pkg.tar.*'."""
    if not file_name:
        return None

    match = RE_PACMAN_PKG_FILE.match(os.path.basename(file_name))
    return match.group('name') if match else None


def parse_pacman_package_names(file_names: Iterable[str]) -> List[str]:
    names = []

    for file_name in file_names or ():
        name = parse_pacman_package_name(file_name)

        if name and name not in names:
            names.append(name)

    return names


def parse_pipx_installed_names(output: Optional[str]) -> List[str]:
    """Nombres de las aplicaciones que pipx declara haber instalado."""
    names = []

    for match in RE_PIPX_INSTALLED.finditer(output or ''):
        name = match.group('name')

        if name not in names:
            names.append(name)

    return names


def parse_cargo_installed_names(output: Optional[str]) -> List[str]:
    """Nombres de los crates que cargo declara haber instalado."""
    names = []

    for pattern in (RE_CARGO_INSTALLED, RE_CARGO_INSTALLING):
        for line in (output or '').splitlines():
            match = pattern.search(line)

            if match:
                name = match.group('name')

                if name not in names:
                    names.append(name)

        if names:
            break

    return names


def read_cargo_package_name(content: Optional[str]) -> Optional[str]:
    """Lee ``name`` de la sección ``[package]`` de un Cargo.toml."""
    section = None

    for line in (content or '').splitlines():
        section_match = RE_CARGO_SECTION.match(line)

        if section_match:
            section = section_match.group('section').strip()
            continue

        if section == 'package':
            name_match = RE_CARGO_NAME.match(line)

            if name_match:
                return name_match.group('name')

    return None


class InstallationRegistry:
    """Persiste, por repositorio, el método usado y los artefactos instalados."""

    def __init__(self, file_path: str = INSTALLED_FILE, logger=None):
        self.file_path = file_path
        self.logger = logger

    @staticmethod
    def key_for(owner: Optional[str], repo_name: Optional[str]) -> str:
        return f'{owner or "?"}/{repo_name or "?"}'

    def read(self) -> Dict[str, dict]:
        if not os.path.isfile(self.file_path):
            return {}

        try:
            with open(self.file_path) as file:
                data = json.load(file)

            return data if isinstance(data, dict) else {}
        except Exception:
            if self.logger:
                self.logger.error(f"No se pudo leer el registro {self.file_path}")
                self.logger.error(traceback.format_exc())

            return {}

    def _write(self, data: Dict[str, dict]) -> bool:
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            with open(self.file_path, 'w') as file:
                json.dump(data, file, indent=2, sort_keys=True)

            return True
        except Exception:
            if self.logger:
                self.logger.error(f"No se pudo escribir el registro {self.file_path}")
                self.logger.error(traceback.format_exc())

            return False

    def get(self, key: str) -> Optional[dict]:
        return self.read().get(key)

    def record(self, key: str, build_method: Optional[str], artifacts: Iterable[str],
               clone_path: Optional[str] = None, repo_url: Optional[str] = None) -> bool:
        data = self.read()
        data[key] = {'build_method': build_method,
                     'artifacts': list(artifacts or []),
                     'clone_path': clone_path,
                     'repo_url': repo_url}
        return self._write(data)

    def remove(self, key: str) -> bool:
        data = self.read()

        if key not in data:
            return True

        del data[key]
        return self._write(data)

    def clear(self) -> bool:
        if not os.path.isfile(self.file_path):
            return True

        try:
            os.remove(self.file_path)
            return True
        except Exception:
            if self.logger:
                self.logger.error(f"No se pudo eliminar el registro {self.file_path}")
                self.logger.error(traceback.format_exc())

            return False
