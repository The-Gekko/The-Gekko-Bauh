"""Tests del módulo consolidado ``bauh.view.qt.thread`` (hallazgos F14 y F32 de la auditoría).

* F14: ``bauh/view/qt/thread.py`` es el único módulo de hilos Qt; el paquete ``threads/``
  (cinco copias byte-idénticas del módulo) ya no existe y no deben reaparecer duplicados.
* F32: ``AsyncAction.run()`` es una plantilla que captura las excepciones de ``_run()``,
  las registra, avisa al usuario y garantiza la emisión de ``signal_finished``.
"""
import hashlib
import importlib.util
import logging
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import bauh.view.qt as qt_package
from bauh.api.abstract.view import MessageType

PYQT_AVAILABLE = importlib.util.find_spec('PyQt5') is not None
QT_DIR = Path(qt_package.__file__).parent
MODULE_LOGGER = 'bauh.view.qt.thread'

# Nombres que exportaban thread.py y threads/__init__.py antes de la consolidación
EXPORTED_NAMES = ('AsyncAction', 'UpgradeSelected', 'UninstallPackage', 'DowngradePackage', 'InstallPackage',
                  'IgnorePackageUpdates', 'CustomAction', 'RefreshApps', 'FindSuggestions', 'SearchPackages',
                  'ShowPackageInfo', 'ShowPackageHistory', 'ShowScreenshots', 'AnimateProgress',
                  'NotifyPackagesReady', 'NotifyInstalledLoaded', 'ListWarnings', 'LaunchPackage',
                  'ApplyFilters', 'SaveTheme', 'StartAsyncAction', 'URLFileDownloader', 'CustomSoftwareAction')


class ThreadModuleLayoutTest(unittest.TestCase):
    """F14: disposición del upstream restaurada, sin copias del módulo."""

    def test_threads_package_removed(self):
        # Se comprueba la ausencia de fuentes, no del directorio: un __pycache__ obsoleto de una
        # instalación anterior puede dejar la carpeta vacía en el árbol de trabajo.
        sources = sorted(p.name for p in (QT_DIR / 'threads').glob('*.py'))
        self.assertEqual([], sources, "el paquete bauh/view/qt/threads no debe tener fuentes")
        self.assertIsNone(importlib.util.find_spec('bauh.view.qt.threads'))
        self.assertTrue((QT_DIR / 'thread.py').is_file())

    def test_no_duplicated_modules_under_view_qt(self):
        digests = {}

        for path in sorted(QT_DIR.rglob('*.py')):
            content = path.read_bytes()

            if content.strip():  # los __init__.py vacíos son legítimamente idénticos entre sí
                digest = hashlib.md5(content).hexdigest()
                digests.setdefault(digest, []).append(str(path.relative_to(QT_DIR)))

        duplicated = [paths for paths in digests.values() if len(paths) > 1]
        self.assertEqual([], duplicated, f"módulos duplicados por md5 bajo bauh/view/qt: {duplicated}")


@unittest.skipUnless(PYQT_AVAILABLE, 'PyQt5 no disponible')
class ThreadModuleExportsTest(unittest.TestCase):
    """F14/F32: nombres exportados y patrón run()/_run() de las subclases."""

    @classmethod
    def setUpClass(cls):
        from bauh.view.qt import thread
        cls.thread = thread

    def test_exports_every_previous_name(self):
        missing = [name for name in EXPORTED_NAMES if not hasattr(self.thread, name)]
        self.assertEqual([], missing, f"nombres que ya no exporta bauh.view.qt.thread: {missing}")

    def test_custom_software_action_is_the_api_class(self):
        from bauh.api.abstract.model import CustomSoftwareAction
        self.assertIs(self.thread.CustomSoftwareAction, CustomSoftwareAction)

    def test_async_action_subclasses_implement_run_template(self):
        from PyQt5.QtCore import QThread

        async_subclasses, other_threads = [], []

        for obj in vars(self.thread).values():
            if isinstance(obj, type) and obj.__module__ == self.thread.__name__ and issubclass(obj, QThread):
                if issubclass(obj, self.thread.AsyncAction):
                    if obj is not self.thread.AsyncAction:
                        async_subclasses.append(obj)
                else:
                    other_threads.append(obj)

        self.assertIn('run', vars(self.thread.AsyncAction))
        self.assertIn('_run', vars(self.thread.AsyncAction))
        self.assertGreaterEqual(len(async_subclasses), 14)
        self.assertGreaterEqual(len(other_threads), 7)

        for cls in async_subclasses:
            self.assertNotIn('run', vars(cls), f"{cls.__name__} debe implementar _run(), no run()")
            self.assertIn('_run', vars(cls), f"{cls.__name__} no implementa _run()")

        for cls in other_threads:  # los QThread ajenos a AsyncAction conservan su run() original
            self.assertIn('run', vars(cls), f"{cls.__name__} debe conservar run()")
            self.assertNotIn('_run', vars(cls), f"{cls.__name__} no debe definir _run()")


@unittest.skipUnless(PYQT_AVAILABLE, 'PyQt5 no disponible')
class AsyncActionErrorHandlingTest(unittest.TestCase):
    """F32: un fallo inesperado del gem no bloquea la ventana ni aborta el proceso."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt5.QtWidgets import QApplication

        from bauh.view.qt import thread
        cls.app = QApplication.instance() or QApplication([])
        cls.thread = thread

    def setUp(self):
        self.i18n = MagicMock()
        self.i18n.__getitem__.side_effect = lambda key: key  # cada texto visible es su propia clave i18n
        self.pkg = MagicMock()
        self.pkg.model.is_update_ignored.return_value = False

    def _collect(self, worker):
        finished, messages = [], []
        worker.signal_finished.connect(lambda res: finished.append(res))
        worker.signal_message.connect(lambda msg: messages.append(msg))
        return finished, messages

    def _run_failing(self, worker, logger_name: str = MODULE_LOGGER):
        finished, messages = self._collect(worker)

        with self.assertLogs(logger_name, level='ERROR') as logs:
            worker.run()  # se ejecuta en el hilo actual: las señales se entregan de forma síncrona

        return finished, messages, logs

    def test_show_package_info_finishes_and_reports_when_manager_raises(self):
        manager = MagicMock()
        manager.get_info.side_effect = RuntimeError('gem exploded <b>')
        worker = self.thread.ShowPackageInfo(i18n=self.i18n, manager=manager, pkg=self.pkg)

        finished, messages, logs = self._run_failing(worker)

        self.assertEqual([None], finished)
        self.assertEqual(1, len(messages))
        self.assertEqual(MessageType.ERROR, messages[0]['type'])
        self.assertEqual('Error', messages[0]['title'])
        self.assertIn('action.failed', messages[0]['body'])
        self.assertIn('RuntimeError: gem exploded &lt;b&gt;', messages[0]['body'])
        self.assertIn('ShowPackageInfo', logs.output[0])
        self.assertIn('Traceback', logs.output[0])

    def test_find_suggestions_finishes_with_empty_result(self):
        man = MagicMock()
        man.list_suggestions.side_effect = KeyError('missing')
        worker = self.thread.FindSuggestions(i18n=self.i18n, man=man)

        finished, messages, _ = self._run_failing(worker)

        self.assertEqual([{'pkgs_found': [], 'error': None}], finished)
        self.assertEqual(1, len(messages))

    def test_show_screenshots_finishes_with_package_reference(self):
        manager = MagicMock()
        manager.get_screenshots.side_effect = ValueError('bad json')
        worker = self.thread.ShowScreenshots(i18n=self.i18n, manager=manager, pkg=self.pkg)

        finished, _, _ = self._run_failing(worker)

        self.assertEqual(1, len(finished))
        self.assertIs(self.pkg, finished[0]['pkg'])
        self.assertEqual((), finished[0]['screenshots'])

    def test_apply_filters_finishes_and_uses_its_own_logger(self):
        filters = MagicMock()
        filters.anything = True
        filters.display_limit = 'not-a-number'  # provoca un TypeError dentro de _run()
        worker = self.thread.ApplyFilters(i18n=self.i18n, logger=logging.getLogger('test.filters'),
                                          filters=filters, pkgs=[MagicMock()], index={'pkg': 1})

        finished, messages, logs = self._run_failing(worker, logger_name='test.filters')

        self.assertEqual([None], finished)
        self.assertEqual(1, len(messages))
        self.assertIn('ApplyFilters', logs.output[0])

    def test_ignore_updates_error_result_keeps_the_initial_package(self):
        manager = MagicMock()
        manager.ignore_update.side_effect = OSError('disk full')
        worker = self.thread.IgnorePackageUpdates(i18n=self.i18n, manager=manager, pkg=self.pkg)

        finished, _, _ = self._run_failing(worker)

        # _run() limpia self.pkg en un finally: el valor seguro debe conservar el paquete original
        self.assertEqual([{'action': 'ignore_updates', 'success': False, 'pkg': self.pkg}], finished)
        self.assertIsNone(worker.pkg)

    def test_custom_action_error_result_matches_handler_contract(self):
        manager = MagicMock()
        manager.execute_custom_action.side_effect = ValueError('boom')
        custom_action = MagicMock()
        custom_action.backup = False
        worker = self.thread.CustomAction(manager=manager, i18n=self.i18n, custom_action=custom_action, pkg=self.pkg)

        finished, _, _ = self._run_failing(worker)

        self.assertEqual([{'success': False, 'pkg': self.pkg, 'action': custom_action,
                           'error': None, 'error_type': MessageType.ERROR}], finished)

    def test_search_already_notified_in_finally_is_not_notified_twice(self):
        manager = MagicMock()
        manager.search.side_effect = KeyError('index')
        worker = self.thread.SearchPackages(i18n=self.i18n, manager=manager)
        worker.word = 'firefox'

        finished, messages, _ = self._run_failing(worker)

        self.assertEqual([{'pkgs_found': [], 'error': None}], finished)
        self.assertEqual(1, len(messages))
        self.assertIsNone(worker.word)

    def test_uses_the_manager_context_logger_when_available(self):
        manager = MagicMock()
        manager.context.logger = logging.getLogger('test.context')
        manager.get_info.side_effect = RuntimeError('boom')
        worker = self.thread.ShowPackageInfo(i18n=self.i18n, manager=manager, pkg=self.pkg)

        finished, _, logs = self._run_failing(worker, logger_name='test.context')

        self.assertEqual([None], finished)
        self.assertIn('RuntimeError: boom', logs.output[0])

    def test_successful_run_notifies_once_without_messages(self):
        manager = MagicMock()
        manager.get_info.return_value = {'version': '1.0'}
        worker = self.thread.ShowPackageInfo(i18n=self.i18n, manager=manager, pkg=self.pkg)
        finished, messages = self._collect(worker)

        worker.run()

        self.assertEqual([{'__app__': self.pkg, 'version': '1.0'}], finished)
        self.assertEqual([], messages)

    def test_worker_can_run_again_after_a_failure(self):
        manager = MagicMock()
        manager.get_info.side_effect = [RuntimeError('boom'), {'version': '2.0'}]
        worker = self.thread.ShowPackageInfo(i18n=self.i18n, manager=manager, pkg=self.pkg)
        finished, _ = self._collect(worker)

        with self.assertLogs(MODULE_LOGGER, level='ERROR'):
            worker.run()

        worker.pkg = self.pkg
        worker.run()

        self.assertEqual([None, {'__app__': self.pkg, 'version': '2.0'}], finished)

    def test_notification_before_the_failure_is_not_duplicated(self):
        thread_module = self.thread

        class NotifyThenFail(thread_module.AsyncAction):

            def _run(self):
                self.notify_finished('done')
                raise RuntimeError('after notify')

        worker = NotifyThenFail(i18n=self.i18n)

        finished, messages, _ = self._run_failing(worker)

        self.assertEqual(['done'], finished)
        self.assertEqual(1, len(messages))

    def test_base_class_without_run_implementation_still_finishes(self):
        worker = self.thread.AsyncAction(i18n=self.i18n)

        finished, messages, _ = self._run_failing(worker)

        self.assertEqual([None], finished)
        self.assertIn('NotImplementedError', messages[0]['body'])

    def test_failure_while_reporting_the_error_still_finishes(self):
        self.i18n.__getitem__.side_effect = KeyError('no i18n')
        manager = MagicMock()
        manager.get_info.side_effect = RuntimeError('boom')
        worker = self.thread.ShowPackageInfo(i18n=self.i18n, manager=manager, pkg=self.pkg)

        finished, messages, logs = self._run_failing(worker)

        self.assertEqual([None], finished)
        self.assertEqual([], messages)
        self.assertTrue(any('Could not report the unexpected error' in line for line in logs.output))

    def test_launch_package_notifies_exactly_once(self):
        manager = MagicMock()
        worker = self.thread.LaunchPackage(i18n=self.i18n, manager=manager, pkg=self.pkg)
        finished, messages = self._collect(worker)

        worker.run()
        self.assertEqual([True], finished)

        manager.launch.side_effect = OSError('no executable')

        with self.assertLogs(MODULE_LOGGER, level='ERROR'):
            worker.run()

        self.assertEqual([True, False], finished)
        self.assertEqual([], messages)  # el fallo al lanzar se trata internamente sin diálogo


if __name__ == '__main__':
    unittest.main()
