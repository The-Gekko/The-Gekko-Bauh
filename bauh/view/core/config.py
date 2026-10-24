from bauh.api.paths import CONFIG_DIR
from bauh.commons.config import YAMLConfigManager

FILE_PATH = f'{CONFIG_DIR}/config.yml'

BACKUP_DEFAULT_REMOVE_METHOD = 'self'
BACKUP_REMOVE_METHODS = {BACKUP_DEFAULT_REMOVE_METHOD, 'all'}

# tema por defecto del fork
DEFAULT_THEME = 'aurora'

# temas heredados del bauh original que el fork retiró: no seguían su diseño y nadie los
# mantenía. Quien tuviera uno elegido pasa al tema por defecto en vez de quedarse sin estilo.
RETIRED_THEMES = ('darcula', 'knight', 'sublime')


class CoreConfigManager(YAMLConfigManager):

    def __init__(self):
        super(CoreConfigManager, self).__init__(config_file_path=FILE_PATH)

    def read_config(self) -> dict:
        config = super(CoreConfigManager, self).read_config()

        if config:
            ui_config = config.get('ui')

            # La pestaña «Personalización» se retiró (los temas y Matugen ya cubren lo que
            # hacía): sus valores se descartan para que no sigan arrastrándose en el fichero.
            config.pop('custom_theme', None)
            # las sugerencias de paquetes también se retiraron (listas sin mantener desde 2022)
            config.pop('suggestions', None)

            if isinstance(ui_config, dict):
                ui_config.pop('custom_theme', None)

            if isinstance(ui_config, dict) and ui_config.get('theme') in RETIRED_THEMES:
                ui_config['theme'] = DEFAULT_THEME

        return config

    def get_default_config(self) -> dict:
        return {
            'gems': None,
            'memory_cache': {
                'data_expiration': 60 * 60,
                'icon_expiration': 60 * 5
            },
            'locale': None,
            'updates': {
                'check_interval': 5,
                'ask_for_reboot': True
            },
            'system': {
                'notifications': True,
                'single_dependency_checking': False
            },
            'ui': {
                'table': {
                    'max_displayed': 50
                },
                'tray': {
                    'default_icon': None,
                    'updates_icon': None
                },
                'qt_style': 'fusion',
                "auto_scale": False,
                "scale_factor": 1.0,
                'theme': DEFAULT_THEME,
                'system_theme': False
            },
            'download': {
                'multithreaded': False,
                'multithreaded_client': None,
                'icons': True
            },
            'store_root_password': True,
            'disk': {
                'trim': {
                    'after_upgrade': False
                }
            },
            'backup': {
                'enabled': True,
                'install': None,
                'uninstall': None,
                'downgrade': None,
                'upgrade': None,
                'mode': 'incremental',
                'type': 'rsync',
                'remove_method': 'self'
            },
            'boot': {
                'load_apps': True
            }
        }
