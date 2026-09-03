import faulthandler
import locale
import logging
import os
import signal
import sys
import traceback
from typing import Optional

import urllib3
from PyQt5.QtCore import QCoreApplication, Qt, QTimer

from bauh import __app_name__, app_args
from bauh.view.core.config import CoreConfigManager
from bauh.view.util import logs

# mensajes de Qt considerados ruido conocido: se descartan de stderr pero se registran a nivel debug
FILTERED_QT_MESSAGES = ('Ignoring XDG_SESSION_TYPE=wayland',
                        'QSocketNotifier: Can only be used with threads started with QThread',
                        'invalid style override',
                        'Wayland does not support QWindow::requestActivate')

# QtMsgType -> etiqueta legible (los valores numericos son estables en Qt5)
QT_MESSAGE_LEVELS = {0: 'debug', 1: 'warning', 2: 'critical', 3: 'fatal', 4: 'info'}

_logger: Optional[logging.Logger] = None
_signal_timer: Optional[QTimer] = None


def qt_message_handler(mode, context, message):
    """Encamina los mensajes de Qt conservando su nivel y registrando lo que se filtra."""
    level = QT_MESSAGE_LEVELS.get(int(mode), 'unknown')

    for filtered in FILTERED_QT_MESSAGES:
        if filtered in message:
            if _logger is not None:
                origin = f'{context.file}:{context.line}' if context and context.file else 'unknown'
                _logger.debug(f'[qt:{level}] filtered message ({origin}): {message}')
            return

    sys.stderr.write(f'[qt:{level}] {message}\n')


def _show_error_dialog(exc_type, exc_value) -> bool:
    """Muestra el error en un dialogo Qt. Devuelve False si no ha sido posible."""
    try:
        from PyQt5.QtWidgets import QApplication

        if QApplication.instance() is None:
            return False

        from bauh.api.abstract.view import MessageType
        from bauh.context import generate_i18n
        from bauh.view.qt import dialog
        from bauh.view.util import resource

        i18n = generate_i18n(CoreConfigManager().get_config(), resource.get_path('locale'))
        body = '<p>{}</p><p>{}: {}</p>'.format(i18n['manage_window.error.unexpected.body'],
                                               exc_type.__name__, exc_value)
        dialog.show_message(title=i18n['error'].capitalize(), body=body, type_=MessageType.ERROR)
        return True
    except Exception:
        return False


def new_excepthook(logger: logging.Logger):
    """Genera un manejador global de excepciones que registra en vez de dejar abortar a PyQt5."""

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        logger.error('Unhandled exception', exc_info=(exc_type, exc_value, exc_tb))
        traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)

        if not _show_error_dialog(exc_type, exc_value):
            logger.debug('Could not display the unhandled exception dialog')

    return _excepthook


def install_signal_handlers(app: QCoreApplication, widget, logger: logging.Logger) -> Optional[QTimer]:
    """Instala manejadores de SIGINT/SIGTERM que cierran la aplicacion de forma ordenada."""

    def _handle_signal(signum, _frame):
        try:
            name = signal.Signals(signum).name
        except ValueError:
            name = str(signum)

        logger.info(f'signal {name} received: shutting down')

        closed = True
        try:
            if hasattr(widget, 'quit_application'):
                widget.quit_application()
            elif hasattr(widget, 'close'):
                closed = bool(widget.close())
        except Exception:
            logger.exception('Could not close the main widget')

        if closed or signum == signal.SIGTERM:
            app.quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except (ValueError, OSError):
            logger.warning(f'Could not install a handler for signal {sig}')

    # el interprete solo atiende senales al volver a Python: un temporizador inactivo
    # obliga al bucle de eventos de Qt a cederle el control periodicamente
    timer = QTimer()
    timer.setInterval(200)
    timer.timeout.connect(lambda: None)
    timer.start()
    return timer


def main(tray: bool = False):
    global _logger, _signal_timer

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
    _logger = logger
    sys.excepthook = new_excepthook(logger)

    try:
        locale.setlocale(locale.LC_NUMERIC, '')
    except Exception:
        logger.error("Could not set locale 'LC_NUMBERIC' to '' to display localized numbers")
        logging.error("Exception occurred", exc_info=True)

    # en sesiones Wayland se pide explicitamente el plugin nativo (Qt5 cae a XWayland por defecto).
    # se respeta cualquier valor previo de QT_QPA_PLATFORM (p. ej. 'offscreen' en los tests)
    if os.getenv('XDG_SESSION_TYPE') == 'wayland' and not os.getenv('QT_QPA_PLATFORM'):
        os.environ['QT_QPA_PLATFORM'] = 'wayland'
        logger.info("Wayland session detected: QT_QPA_PLATFORM set to 'wayland'")

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
        logging.error("Exception occurred", exc_info=True)

    if bool(app_config['ui']['hdpi']):
        logger.info("HDPI settings activated")
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    if bool(args.suggestions):
        logger.info("Forcing loading software suggestions after the initialization process")

    if tray or bool(args.tray):
        from bauh.view.qt.systray import acquire_single_instance_lock

        if not acquire_single_instance_lock(logger):
            logger.warning('another tray icon is already running: exiting')
            sys.exit(0)

        from bauh.tray import new_tray_icon
        app, widget = new_tray_icon(app_config, logger)
    else:
        from bauh.manage import new_manage_panel
        app, widget = new_manage_panel(args, app_config, logger)

        if not bool(args.settings) and not bool(args.reset):
            # permite a la bandeja saber que ya hay una ventana de gestion viva
            # (incluso si la lanzo otro proceso tras un reinicio de la aplicacion)
            from bauh.view.core.tray_client import register_manage_window
            register_manage_window()

    # se conserva la referencia para que el temporizador de senales no sea recolectado
    _signal_timer = install_signal_handlers(app=app, widget=widget, logger=logger)

    widget.show()
    sys.exit(app.exec_())


def tray():
    main(tray=True)


if __name__ == '__main__':
    main()
