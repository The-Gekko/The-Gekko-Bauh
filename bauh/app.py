import faulthandler
import locale
import os
import sys
import traceback

import urllib3
from PyQt5.QtCore import QCoreApplication, Qt

from bauh import __app_name__, app_args
from bauh.view.core.config import CoreConfigManager
from bauh.view.util import logs

def qt_message_handler(mode, context, message):
    if 'Ignoring XDG_SESSION_TYPE=wayland' in message:
        return
    if 'QSocketNotifier: Can only be used with threads started with QThread' in message:
        return
    if 'invalid style override' in message:
        return
    if 'Wayland does not support QWindow::requestActivate' in message:
        return
    sys.stderr.write(f"{message}\n")


def main(tray: bool = False):
    from PyQt5.QtCore import qInstallMessageHandler
    qInstallMessageHandler(qt_message_handler)
    
    if not os.getenv('PYTHONUNBUFFERED'):
        os.environ['PYTHONUNBUFFERED'] = '1'

    if not os.getenv('XDG_RUNTIME_DIR'):
        os.environ['XDG_RUNTIME_DIR'] = f'/run/user/{os.getuid()}'

    faulthandler.enable()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    args = app_args.read()

    logger = logs.new_logger(__app_name__, bool(args.logs))

    try:
        locale.setlocale(locale.LC_NUMERIC, '')
    except Exception:
        logger.error("Could not set locale 'LC_NUMBERIC' to '' to display localized numbers")
        import logging; logging.error("Exception occurred", exc_info=True)

    if args.offline:
        logger.warning("offline mode activated")

    if os.getenv('XDG_SESSION_TYPE', '').lower() == 'wayland':
        logger.info("Wayland session detected: forcing 'QT_QPA_PLATFORM' to 'wayland'")
        os.environ['QT_QPA_PLATFORM'] = 'wayland'

    app_config = CoreConfigManager().get_config()

    if bool(app_config['ui']['auto_scale']):
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        logger.info("Auto screen scale factor activated")

    try:
        scale_factor = float(app_config['ui']['scale_factor'])
        os.environ['QT_SCALE_FACTOR'] = str(scale_factor)
        logger.info("Scale factor set to {}".format(scale_factor))
    except Exception:
        import logging; logging.error("Exception occurred", exc_info=True)

    if bool(app_config['ui']['hdpi']):
        logger.info("HDPI settings activated")
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    if bool(args.suggestions):
        logger.info("Forcing loading software suggestions after the initialization process")

    if tray or bool(args.tray):
        from bauh.tray import new_tray_icon
        app, widget = new_tray_icon(app_config, logger)
    else:
        from bauh.manage import new_manage_panel
        app, widget = new_manage_panel(args, app_config, logger)

    widget.show()
    sys.exit(app.exec_())


def tray():
    main(tray=True)


if __name__ == '__main__':
    main()
