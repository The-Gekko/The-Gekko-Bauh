import os
import sys

from bauh import ROOT_DIR, __version__, __app_name__ as APP_NAME
from bauh.api import user
from bauh.api.abstract.context import ApplicationContext
from bauh.api.http import HttpClient
from bauh.cli import __app_name__, cli_args
from bauh.migration import migrate_legacy_user_data
from bauh.cli.controller import CLIManager
from bauh.commons.internet import InternetChecker
from bauh.context import generate_i18n, DEFAULT_I18N_KEY
from bauh.view.core import gems, web_legacy
from bauh.view.core.config import CoreConfigManager
from bauh.view.core.controller import GenericSoftwareManager
from bauh.view.core.downloader import AdaptableFileDownloader
from bauh.view.util import logs, util, resource
from bauh.view.util.cache import DefaultMemoryCacheFactory
from bauh.view.util.disk import DefaultDiskCacheLoaderFactory


def main():
    if not os.getenv('PYTHONUNBUFFERED'):
        os.environ['PYTHONUNBUFFERED'] = '1'

    args = cli_args.read()
    logger = logs.new_logger(__app_name__, False)

    if args.command == 'clean-web-apps':
        # no necesita cargar las gems: la gem Web ya no existe y solo quedan ficheros
        sys.exit(clean_web_apps(assume_yes=args.yes))

    # Primera ejecución tras el cambio de nombre: se recuperan los ajustes heredados.
    # Se usa el nombre de la aplicación, no el de la CLI (que lleva el sufijo «-cli» y
    # no corresponde a ningún directorio de datos).
    migrate_legacy_user_data(APP_NAME, logger)

    app_config = CoreConfigManager().get_config()
    http_client = HttpClient(logger)

    i18n = generate_i18n(app_config, resource.get_path('locale'))

    cache_factory = DefaultMemoryCacheFactory(expiration_time=0)

    downloader = AdaptableFileDownloader(logger=logger, multithread_enabled=app_config['download']['multithreaded'],
                                         multithread_client=app_config['download']['multithreaded_client'],
                                         i18n=i18n, http_client=http_client)

    context = ApplicationContext(i18n=i18n,
                                 http_client=http_client,
                                 download_icons=bool(app_config['download']['icons']),
                                 app_root_dir=ROOT_DIR,
                                 cache_factory=cache_factory,
                                 disk_loader_factory=DefaultDiskCacheLoaderFactory(logger),
                                 logger=logger,
                                 distro=util.get_distro(),
                                 file_downloader=downloader,
                                 app_name=__app_name__,
                                 app_version=__version__,
                                 internet_checker=InternetChecker(offline=False),
                                 root_user=user.is_root())

    managers = gems.load_managers(context=context, locale=i18n.current_key, config=app_config,
                                  default_locale=DEFAULT_I18N_KEY, logger=logger)

    cli = CLIManager(GenericSoftwareManager(managers, context=context, config=app_config))

    if args.command == 'updates':
        cli.list_updates(args.format)


def clean_web_apps(assume_yes: bool) -> int:
    """Borra los restos de la antigua gem Web. Devuelve el código de salida."""
    paths = web_legacy.leftovers()

    if not paths:
        print(f'[{__app_name__}] No web apps left by the retired Web gem')
        return 0

    apps = web_legacy.installed_apps()
    print(f'[{__app_name__}] The Web gem was retired (nativefier is abandoned since 2023).')

    if apps:
        print(f'[{__app_name__}] Installed web apps: {", ".join(apps)}')

    print(f'[{__app_name__}] These files and directories will be removed:')

    for path in paths:
        print(f'  {path}')

    if not assume_yes:
        try:
            answer = input('Continue? [y/N] ').strip().lower()
        except EOFError:
            answer = ''

        if answer not in ('y', 'yes', 's', 'si', 'sí'):
            print(f'[{__app_name__}] Nothing removed')
            return 1

    failed = web_legacy.remove()

    for path in failed:
        print(f'[{__app_name__}] Could not remove {path}')

    if not failed:
        print(f'[{__app_name__}] Web apps removed')

    return 1 if failed else 0


if __name__ == '__main__':
    main()
