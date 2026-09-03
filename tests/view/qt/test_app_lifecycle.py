import importlib.util
import io
import logging
import os
import signal
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

if PYQT5_AVAILABLE:
    from PyQt5.QtGui import QCloseEvent
    from PyQt5.QtWidgets import QApplication

    from bauh import app as bauh_app
    from bauh.api.abstract.context import ApplicationContext
    from bauh.api.abstract.controller import SoftwareManager
    from bauh.view.qt import prepare
    from bauh.view.util.translation import I18n


def new_qt_context(file_: str = '/tmp/some.cpp', line: int = 10):
    context = MagicMock()
    context.file = file_
    context.line = line
    return context


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestQtMessageHandler(unittest.TestCase):

    def tearDown(self):
        bauh_app._logger = None

    def test_the_message_level_is_included_in_the_output(self):
        stderr = io.StringIO()

        with patch('sys.stderr', stderr):
            bauh_app.qt_message_handler(1, new_qt_context(), 'some unexpected warning')

        self.assertIn('[qt:warning]', stderr.getvalue())
        self.assertIn('some unexpected warning', stderr.getvalue())

    def test_filtered_messages_are_logged_instead_of_dropped(self):
        logger = MagicMock(spec=logging.Logger)
        bauh_app._logger = logger
        stderr = io.StringIO()

        with patch('sys.stderr', stderr):
            bauh_app.qt_message_handler(1, new_qt_context(),
                                        'QSocketNotifier: Can only be used with threads started with QThread')

        self.assertEqual('', stderr.getvalue())
        logger.debug.assert_called_once()
        self.assertIn('filtered message', logger.debug.call_args.args[0])

    def test_an_unknown_level_does_not_break_the_handler(self):
        stderr = io.StringIO()

        with patch('sys.stderr', stderr):
            bauh_app.qt_message_handler(99, new_qt_context(), 'weird')

        self.assertIn('[qt:unknown]', stderr.getvalue())


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestExceptHook(unittest.TestCase):

    def test_the_exception_is_logged_with_its_traceback(self):
        logger = MagicMock(spec=logging.Logger)
        hook = bauh_app.new_excepthook(logger)

        try:
            raise ValueError('boom')
        except ValueError as e:
            exc_info = (type(e), e, e.__traceback__)

        with patch.object(bauh_app, '_show_error_dialog', return_value=True), patch('sys.stderr', io.StringIO()):
            hook(*exc_info)

        logger.error.assert_called_once()
        self.assertEqual(exc_info, logger.error.call_args.kwargs['exc_info'])

    def test_keyboard_interrupt_is_delegated_to_the_default_hook(self):
        logger = MagicMock(spec=logging.Logger)
        hook = bauh_app.new_excepthook(logger)

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt as e:
            exc_info = (type(e), e, e.__traceback__)

        with patch('sys.__excepthook__') as default_hook:
            hook(*exc_info)

        default_hook.assert_called_once()
        logger.error.assert_not_called()


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestSignalHandlers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}

    def tearDown(self):
        for sig, handler in self.previous.items():
            signal.signal(sig, handler)

    def test_handlers_are_installed_for_sigint_and_sigterm(self):
        widget = MagicMock()
        widget.close.return_value = True
        logger = MagicMock(spec=logging.Logger)

        timer = bauh_app.install_signal_handlers(app=MagicMock(), widget=widget, logger=logger)

        try:
            self.assertIsNotNone(timer)
            self.assertTrue(timer.isActive())

            for sig in (signal.SIGINT, signal.SIGTERM):
                self.assertTrue(callable(signal.getsignal(sig)))
        finally:
            timer.stop()

    def test_sigterm_quits_even_if_the_widget_refuses_to_close(self):
        widget = MagicMock(spec=['close'])
        widget.close.return_value = False
        app = MagicMock()

        timer = bauh_app.install_signal_handlers(app=app, widget=widget, logger=MagicMock(spec=logging.Logger))

        try:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        finally:
            timer.stop()

        widget.close.assert_called_once()
        app.quit.assert_called_once()

    def test_sigint_does_not_quit_when_the_window_refuses_to_close(self):
        widget = MagicMock(spec=['close'])
        widget.close.return_value = False
        app = MagicMock()

        timer = bauh_app.install_signal_handlers(app=app, widget=widget, logger=MagicMock(spec=logging.Logger))

        try:
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        finally:
            timer.stop()

        app.quit.assert_not_called()

    def test_the_tray_is_shut_down_through_its_own_method(self):
        widget = MagicMock(spec=['quit_application'])
        app = MagicMock()

        timer = bauh_app.install_signal_handlers(app=app, widget=widget, logger=MagicMock(spec=logging.Logger))

        try:
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        finally:
            timer.stop()

        widget.quit_application.assert_called_once()


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestPreparePanel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        i18n = MagicMock(spec=I18n)
        i18n.get.side_effect = lambda key, default=None: default if default is not None else key
        i18n.__getitem__.side_effect = lambda key: key

        self.context = MagicMock(spec=ApplicationContext)
        self.context.logger = logging.getLogger('test')

        self.panel = prepare.PreparePanel(context=self.context,
                                          manager=MagicMock(spec=SoftwareManager),
                                          i18n=i18n,
                                          manage_window=MagicMock(),
                                          app_config={'boot': {'load_apps': False}})

    def tearDown(self):
        self.panel.deleteLater()

    def test_closing_the_panel_stops_its_threads(self):
        event = QCloseEvent()

        with patch.object(prepare, 'ConfirmationDialog') as dialog_cls, \
                patch.object(prepare.QCoreApplication, 'exit') as exit_app, \
                patch.object(self.panel, 'stop_threads') as stop_threads:
            dialog_cls.return_value.ask.return_value = True
            self.panel.closeEvent(event)

        stop_threads.assert_called_once_with(include_prepare=True)
        exit_app.assert_called_once()

    def test_closing_the_panel_can_be_cancelled(self):
        event = QCloseEvent()
        event.accept()
        self.panel.prepare_thread = MagicMock()
        self.panel.prepare_thread.isRunning.return_value = True

        with patch.object(prepare, 'ConfirmationDialog') as dialog_cls, \
                patch.object(prepare.QCoreApplication, 'exit') as exit_app, \
                patch.object(self.panel, 'stop_threads') as stop_threads:
            dialog_cls.return_value.ask.return_value = False
            self.panel.closeEvent(event)

        self.assertFalse(event.isAccepted())
        stop_threads.assert_not_called()
        exit_app.assert_not_called()

    def test_the_preparation_thread_survives_a_self_close(self):
        # al saltar las tareas iniciales la preparacion debe continuar en segundo plano
        self.panel.self_close = True

        with patch.object(self.panel, 'stop_threads') as stop_threads:
            self.panel.closeEvent(QCloseEvent())

        stop_threads.assert_called_once_with()

    def test_the_skip_thread_stops_before_its_ten_second_timeout(self):
        thread = self.panel.skip_thread
        thread.start()
        thread.requestInterruption()

        self.assertTrue(thread.wait(3000))
        self.assertFalse(thread.isRunning())

    def test_the_check_thread_stops_before_its_tasks_finish(self):
        thread = self.panel.check_thread
        thread.total = 1  # nunca se alcanzara: solo la interrupcion puede sacarlo del bucle
        finished = []
        thread.signal_finished.connect(finished.append)

        thread.start()
        thread.requestInterruption()

        self.assertTrue(thread.wait(3000))
        self.assertFalse(thread.isRunning())
        self.assertEqual([], finished)

    def test_cancelling_the_root_password_exits_with_code_one(self):
        thread = self.panel.prepare_thread
        thread.manager.requires_root.return_value = True
        thread.ask_password = MagicMock(return_value=(False, None))

        with patch.object(prepare.user, 'is_root', return_value=False), \
                patch.object(prepare, 'QMetaObject') as meta_object, \
                patch.object(prepare, 'Q_ARG') as q_arg:
            thread.run()

        meta_object.invokeMethod.assert_called_once()
        self.assertEqual('exit', meta_object.invokeMethod.call_args.args[1])
        q_arg.assert_called_once_with(int, 1)
        thread.manager.prepare.assert_not_called()


if __name__ == '__main__':
    unittest.main()
