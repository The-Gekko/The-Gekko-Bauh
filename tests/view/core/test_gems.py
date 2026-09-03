import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh.view.core import gems

MODULE_NAME = 'bauh.gems.example_test_gem.controller'


class GemsLoaderTest(TestCase):

    def setUp(self):
        sys.modules.pop(MODULE_NAME, None)
        self.addCleanup(sys.modules.pop, MODULE_NAME, None)
        self.context = SimpleNamespace(i18n=SimpleNamespace(current={}, default={}))

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='example', path='/tmp/example'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    @patch.object(gems, 'find_manager')
    def test_load_managers__must_execute_and_register_the_module_spec(self, find_manager, module_from_spec, find_spec,
                                                                       scandir, read_forbidden_gems):
        loader = Mock()
        spec = SimpleNamespace(loader=loader, name=MODULE_NAME)
        module = object()
        manager = Mock()
        manager.is_default_enabled.return_value = True
        manager_class = Mock(return_value=manager)

        find_spec.return_value = spec
        module_from_spec.return_value = module
        find_manager.return_value = manager_class

        managers = gems.load_managers(locale=None, context=self.context, config={'gems': None}, default_locale='en',
                                      logger=Mock())

        self.assertEqual([manager], managers)
        module_from_spec.assert_called_once_with(spec)
        loader.exec_module.assert_called_once_with(module)
        manager.set_enabled.assert_called_once_with(True)
        # el módulo queda registrado para que imports posteriores reutilicen la misma copia
        self.assertIs(module, sys.modules.get(MODULE_NAME))

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='example', path='/tmp/example'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    @patch.object(gems, 'find_manager')
    def test_load_managers__must_reuse_a_module_already_imported(self, find_manager, module_from_spec, find_spec,
                                                                 scandir, read_forbidden_gems):
        loader = Mock()
        existing_module = object()
        sys.modules[MODULE_NAME] = existing_module
        manager = Mock()
        manager.is_default_enabled.return_value = False
        manager_class = Mock(return_value=manager)

        find_spec.return_value = SimpleNamespace(loader=loader, name=MODULE_NAME)
        find_manager.return_value = manager_class

        managers = gems.load_managers(locale=None, context=self.context, config={'gems': None}, default_locale='en',
                                      logger=Mock())

        self.assertEqual([manager], managers)
        module_from_spec.assert_not_called()
        loader.exec_module.assert_not_called()
        find_manager.assert_called_once_with(existing_module)
        manager.set_enabled.assert_called_once_with(False)
        self.assertIs(existing_module, sys.modules.get(MODULE_NAME))

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='example', path='/tmp/example'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    @patch.object(gems, 'find_manager')
    def test_load_managers__must_enable_only_the_gems_listed_in_the_config(self, find_manager, module_from_spec,
                                                                          find_spec, scandir, read_forbidden_gems):
        manager = Mock()
        manager.is_default_enabled.return_value = False
        find_spec.return_value = SimpleNamespace(loader=Mock(), name=MODULE_NAME)
        module_from_spec.return_value = object()
        find_manager.return_value = Mock(return_value=manager)

        gems.load_managers(locale=None, context=self.context, config={'gems': ['example']}, default_locale='en',
                           logger=Mock())

        manager.is_default_enabled.assert_not_called()
        manager.set_enabled.assert_called_once_with(True)

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='broken', path='/tmp/broken'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    def test_load_managers__must_skip_and_unregister_a_gem_that_fails_to_import(self, module_from_spec, find_spec,
                                                                                scandir, read_forbidden_gems):
        loader = Mock()
        loader.exec_module.side_effect = ImportError('missing optional dependency')
        logger = Mock()

        find_spec.return_value = SimpleNamespace(loader=loader, name=MODULE_NAME)
        module_from_spec.return_value = object()

        managers = gems.load_managers(locale=None, context=self.context, config={'gems': None}, default_locale='en',
                                      logger=logger)

        self.assertEqual([], managers)
        logger.exception.assert_called_once()
        # un módulo a medio ejecutar no debe quedar registrado
        self.assertNotIn(MODULE_NAME, sys.modules)
