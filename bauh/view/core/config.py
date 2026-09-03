from bauh.api.paths import CONFIG_DIR
from bauh.commons.config import YAMLConfigManager

FILE_PATH = f'{CONFIG_DIR}/config.yml'

BACKUP_DEFAULT_REMOVE_METHOD = 'self'
BACKUP_REMOVE_METHODS = {BACKUP_DEFAULT_REMOVE_METHOD, 'all'}

# tema por defecto del fork
DEFAULT_THEME = 'aurora'

# única fuente de verdad del esquema de 'custom_theme' (defaults y restablecimiento)
DEFAULT_CUSTOM_THEME = {
    'enabled': False,
    'background_color': '#161B22',
    'text_color': '#FFFFFF',
    'accent_color': '#FF4500',
    'opacity': 100,
    'background_image': None
}


class CoreConfigManager(YAMLConfigManager):

    def __init__(self):
        super(CoreConfigManager, self).__init__(config_file_path=FILE_PATH)

    def read_config(self) -> dict:
        config = super(CoreConfigManager, self).read_config()

        if config:
            ui_config = config.get('ui')
            legacy_theme = ui_config.pop('custom_theme', None) if isinstance(ui_config, dict) else None

            if legacy_theme and 'custom_theme' not in config:
                config['custom_theme'] = legacy_theme

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
            'suggestions': {
                'enabled': True,
                'by_type': 15
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
                'hdpi': True,
                "auto_scale": False,
                "scale_factor": 1.0,
                'theme': DEFAULT_THEME,
                'system_theme': False
            },
            'custom_theme': dict(DEFAULT_CUSTOM_THEME),
            'download': {
                'multithreaded': False,
                'multithreaded_client': None,
                'icons': True,
                'check_ssl': True
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
