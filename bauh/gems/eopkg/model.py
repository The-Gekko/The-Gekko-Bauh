from typing import Iterable, Optional

from bauh.api.abstract.model import CustomSoftwareAction, SoftwarePackage
from bauh.gems.eopkg import get_icon_path


class EopkgPackage(SoftwarePackage):
    """Representa un paquete de Solus OS gestionado por eopkg."""

    def __init__(self, name: str, version: str = None, description: str = None,
                 installed: bool = False, update: bool = False,
                 latest_version: str = None, release: str = None,
                 component: str = None):
        super(EopkgPackage, self).__init__(
            id=name,
            name=name,
            version=version,
            # cuando no se conoce la versión disponible se asume la instalada,
            # de modo que la columna «última versión» nunca quede vacía
            latest_version=latest_version if latest_version else version,
            icon_url=None,
            description=description,
            installed=installed,
            update=update
        )
        self.release = release
        self.component = component

    def __repr__(self):
        return f"EopkgPackage(name={self.name}, version={self.version})"

    def has_history(self):
        return False

    def has_info(self):
        return True

    def can_be_downgraded(self):
        return False

    def get_type(self):
        return 'eopkg'

    def get_default_icon_path(self):
        return self.get_type_icon_path()

    def get_type_icon_path(self):
        return get_icon_path()

    def is_application(self):
        # no hay forma fiable de distinguir aplicaciones de bibliotecas usando sólo la CLI de
        # eopkg sin inspeccionar los .desktop instalados, así que se muestran todas
        return True

    def get_data_to_cache(self) -> dict:
        return {}

    def fill_cached_data(self, data: dict):
        pass

    def can_be_run(self) -> bool:
        return False

    def get_publisher(self) -> str:
        return 'Solus'

    def get_disk_cache_path(self) -> str:
        return None

    def get_disk_icon_path(self):
        return self.get_type_icon_path()

    def has_screenshots(self):
        return False

    def get_name_tooltip(self) -> str:
        return f'{self.name} (Solus OS)'

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
        if isinstance(other, EopkgPackage):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)
