import os
from typing import Iterable, List, Optional

from bauh.api.abstract.model import CustomSoftwareAction, SoftwarePackage
from bauh.commons import resource
from bauh.gems.github import ROOT_DIR


class GitHubPackage(SoftwarePackage):
    """Representa un repositorio de GitHub dentro de bauh."""

    def __init__(self, name: str = None, description: str = None, version: str = None,
                 repo_url: str = None, owner: str = None, repo_name: str = None,
                 stars: int = 0, clone_path: str = None, build_method: str = None,
                 cloned: bool = False, built: bool = False, installed: bool = False,
                 license: str = None, categories=None, default_branch: str = 'main',
                 language: str = None, installed_artifacts: Optional[List[str]] = None,
                 update: bool = False, latest_version: str = None, **kwargs):
        super(GitHubPackage, self).__init__(
            id=repo_url or name,
            name=name,
            version=version,
            latest_version=latest_version if latest_version else version,
            icon_url=None,
            license=license,
            description=description,
            installed=installed,
            update=update
        )
        self.repo_url = repo_url
        self.owner = owner
        self.repo_name = repo_name
        self.stars = stars
        self.clone_path = clone_path
        self.build_method = build_method
        self.cloned = cloned
        self.built = built
        self.default_branch = default_branch
        self.language = language
        self.installed_artifacts = list(installed_artifacts) if installed_artifacts else []
        self.categories = categories if categories else ['GitHub']

    def __repr__(self):
        return f"GitHubPackage(name={self.name}, url={self.repo_url})"

    def has_history(self):
        return False

    def has_info(self):
        return True

    def can_be_downgraded(self):
        return False

    def get_type(self):
        return 'GitHub'

    def get_default_icon_path(self):
        return self.get_type_icon_path()

    def get_type_icon_path(self):
        return resource.get_path('img/github.svg', ROOT_DIR)

    def is_application(self):
        return True

    def get_data_to_cache(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'repo_url': self.repo_url,
            'owner': self.owner,
            'repo_name': self.repo_name,
            'stars': self.stars,
            'clone_path': self.clone_path,
            'build_method': self.build_method,
            'cloned': self.cloned,
            'built': self.built,
            'default_branch': self.default_branch,
            'language': self.language,
            'version': self.version,
            'license': self.license,
            'installed_artifacts': self.installed_artifacts,
        }

    def fill_cached_data(self, data: dict):
        for attr in ('name', 'description', 'repo_url', 'owner', 'repo_name', 'stars',
                     'clone_path', 'build_method', 'cloned', 'built', 'default_branch',
                     'language', 'version', 'license', 'installed_artifacts'):
            val = data.get(attr)

            if val is not None:
                setattr(self, attr, val)

    def can_be_run(self) -> bool:
        # el botón "ejecutar" abre la carpeta del clon en el gestor de archivos
        return bool(self.clone_path) and os.path.isdir(self.clone_path)

    def get_publisher(self) -> str:
        return self.owner or ''

    def get_disk_cache_path(self) -> str:
        return self.clone_path

    def get_disk_icon_path(self):
        return self.get_type_icon_path()

    def has_screenshots(self):
        return False

    def get_name_tooltip(self) -> str:
        if self.owner and self.repo_name:
            return f'{self.owner}/{self.repo_name}'

        return self.repo_url if self.repo_url else self.name

    def get_custom_actions(self) -> Optional[Iterable[CustomSoftwareAction]]:
        return None

    def supports_backup(self) -> bool:
        return False

    def supports_ignored_updates(self) -> bool:
        return False

    def is_update_ignored(self) -> bool:
        return False

    def supports_disk_cache(self) -> bool:
        return False

    def __eq__(self, other):
        if isinstance(other, GitHubPackage):
            return self.repo_url == other.repo_url
        return False

    def __hash__(self):
        return hash(self.repo_url)
