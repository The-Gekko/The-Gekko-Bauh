"""Lectura de metadatos de un clon de git sin lanzar subprocesos.

``read_installed`` recorre todos los clones en cada refresco; leer ``.git/config`` y
``.git/HEAD`` directamente evita dos procesos ``git`` por repositorio.
"""

import os
import re
from typing import Optional

RE_GIT_SECTION = re.compile(r'^\s*\[(?P<section>[^\]]+)\]\s*$')
RE_GIT_URL = re.compile(r'^\s*url\s*=\s*(?P<url>\S.*?)\s*$')
RE_HEAD_REF = re.compile(r'^\s*ref:\s*refs/heads/(?P<branch>.+?)\s*$')

RE_GITHUB_URL = re.compile(r'^https?://(?:www\.)?github\.com/(?P<owner>[^/\s#?]+)/'
                           r'(?P<repo>[^/\s#?]+)/?.*$', re.IGNORECASE)
RE_GITHUB_SSH = re.compile(r'^(?:ssh://)?git@github\.com[:/](?P<owner>[^/\s]+)/'
                           r'(?P<repo>[^/\s]+?)(?:\.git)?/?$', re.IGNORECASE)


def normalize_remote_url(url: Optional[str]) -> Optional[str]:
    """Convierte una URL de remoto a la forma canónica ``https://github.com/owner/repo``."""
    if not url:
        return None

    url = url.strip()

    for pattern in (RE_GITHUB_SSH, RE_GITHUB_URL):
        match = pattern.match(url)

        if match:
            repo = match.group('repo')

            if repo.endswith('.git'):
                repo = repo[:-4]

            return f"https://github.com/{match.group('owner')}/{repo}"

    return url[:-4] if url.endswith('.git') else url


def parse_github_url(url: Optional[str]):
    """Devuelve ``(owner, repo)`` de una URL de GitHub, o ``None``."""
    normalized = normalize_remote_url(url)

    if not normalized:
        return None

    match = RE_GITHUB_URL.match(normalized)

    if not match:
        return None

    return match.group('owner'), match.group('repo')


def same_repository(url_a: Optional[str], url_b: Optional[str]) -> bool:
    """Compara dos URLs de remoto ignorando el protocolo y el sufijo '.git'."""
    normalized_a = normalize_remote_url(url_a)
    normalized_b = normalize_remote_url(url_b)

    if not normalized_a or not normalized_b:
        return False

    return normalized_a.lower() == normalized_b.lower()


def parse_remote_url(config_content: Optional[str],
                     remote: str = 'origin') -> Optional[str]:
    """Extrae la URL de un remoto del contenido de un fichero ``.git/config``."""
    target, section = f'remote "{remote}"', None

    for line in (config_content or '').splitlines():
        section_match = RE_GIT_SECTION.match(line)

        if section_match:
            section = section_match.group('section').strip()
            continue

        if section == target:
            url_match = RE_GIT_URL.match(line)

            if url_match:
                return normalize_remote_url(url_match.group('url'))

    return None


def parse_head_branch(head_content: Optional[str]) -> Optional[str]:
    """Extrae el nombre de la rama del contenido de ``.git/HEAD`` (None si es HEAD suelto)."""
    for line in (head_content or '').splitlines():
        match = RE_HEAD_REF.match(line)

        if match:
            return match.group('branch')

    return None


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, encoding='utf-8', errors='replace') as file:
            return file.read()
    except OSError:
        return None


def read_remote_url(repo_path: str, remote: str = 'origin') -> Optional[str]:
    content = _read_text(os.path.join(repo_path, '.git', 'config'))
    return parse_remote_url(content, remote)


def read_current_branch(repo_path: str) -> Optional[str]:
    content = _read_text(os.path.join(repo_path, '.git', 'HEAD'))
    return parse_head_branch(content)
