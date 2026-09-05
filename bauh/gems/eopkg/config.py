from bauh.commons.config import YAMLConfigManager
from bauh.gems.eopkg import CONFIG_FILE

# número máximo de resultados devueltos por una búsqueda cuando la vista no impone un límite
DEFAULT_SEARCH_LIMIT = 50

# segundos que puede tardar un comando de sólo lectura de eopkg antes de considerarse colgado
DEFAULT_COMMAND_TIMEOUT = 60


class EopkgConfigManager(YAMLConfigManager):

    def __init__(self):
        super(EopkgConfigManager, self).__init__(config_file_path=CONFIG_FILE)

    def get_default_config(self) -> dict:
        return {
            'search_limit': DEFAULT_SEARCH_LIMIT,
            'command_timeout': DEFAULT_COMMAND_TIMEOUT,
            # 'sudo eopkg ur' antes de actualizar, tal y como recomienda el flujo oficial
            'sync_repos_before_upgrade': True,
            # 'sudo eopkg ur' al arrancar: sin él 'eopkg list-upgrades' responde con el índice
            # local, que puede llevar días sin refrescar, y bauh no ve ninguna actualización
            'sync_repos_startup': True,
        }
