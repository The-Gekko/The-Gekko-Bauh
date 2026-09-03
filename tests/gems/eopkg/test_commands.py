import unittest
from unittest.mock import Mock, patch

from bauh.api.abstract.controller import SoftwareAction
from bauh.api.abstract.view import FormComponent
from bauh.gems.eopkg import commands
from bauh.gems.eopkg.controller import EopkgManager
from bauh.gems.eopkg.model import EopkgPackage


class CommandBuildersTest(unittest.TestCase):

    def test_uninstall_command__must_always_use_rmf(self):
        cmd = commands.uninstall_command(['discord'])

        self.assertEqual('eopkg', cmd[0])
        self.assertEqual('rmf', cmd[1])
        self.assertNotIn('remove', cmd)
        self.assertNotIn('rm', cmd)

    def test_uninstall_command__must_be_non_interactive_and_without_color(self):
        cmd = commands.uninstall_command(['discord'])

        self.assertIn('-y', cmd)
        self.assertIn('--no-color', cmd)
        self.assertEqual('discord', cmd[-1])

    def test_install_command(self):
        self.assertEqual(['eopkg', 'it', '--no-color', '-y', 'vlc'],
                         commands.install_command(['vlc']))

    def test_upgrade_command__must_take_every_package_in_one_transaction(self):
        cmd = commands.upgrade_command(['a', 'b', 'c'])

        self.assertEqual(['eopkg', 'up', '--no-color', '-y', 'a', 'b', 'c'], cmd)

    def test_upgrade_command__without_packages_upgrades_the_whole_system(self):
        self.assertEqual(['eopkg', 'up', '--no-color', '-y'], commands.upgrade_command())

    def test_update_repos_command(self):
        self.assertEqual(['eopkg', 'ur', '--no-color'], commands.update_repos_command())

    def test_delete_cache_command(self):
        self.assertEqual(['eopkg', 'dc', '--no-color'], commands.delete_cache_command())

    def test_search_command(self):
        self.assertEqual(['eopkg', 'sr', '--no-color', 'media', 'player'],
                         commands.search_command(['media', 'player']))

    def test_list_installed_command(self):
        self.assertEqual(['eopkg', 'li', '--no-color'], commands.list_installed_command())
        self.assertEqual(['eopkg', 'li', '--no-color', '--install-info'],
                         commands.list_installed_command(install_info=True))

    def test_read_only_commands_must_not_be_non_interactive(self):
        for cmd in (commands.search_command(['x']), commands.list_installed_command(),
                    commands.info_command(['x']), commands.history_command()):
            self.assertNotIn('-y', cmd)
            self.assertIn('--no-color', cmd)


class EopkgManagerTransactionTest(unittest.TestCase):

    def setUp(self):
        context = Mock()
        context.i18n = {}
        self.manager = EopkgManager(context)
        self.manager.configman = Mock()
        self.manager.configman.get_config.return_value = {'search_limit': 50,
                                                          'command_timeout': 60,
                                                          'sync_repos_before_upgrade': False}
        self.manager.i18n = _DummyI18n()

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_uninstall__must_run_eopkg_rmf_with_yes(self, simple_process: Mock,
                                                    process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, 'Removed discord')
        self.manager._read_installed_index = Mock(return_value={})

        result = self.manager.uninstall(EopkgPackage(name='discord'), 'secret', Mock())

        self.assertTrue(result.success)
        cmd = simple_process.call_args[0][0]
        self.assertEqual(['eopkg', 'rmf', '--no-color', '-y', 'discord'], cmd)
        self.assertEqual('secret', simple_process.call_args[1]['root_password'])

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_uninstall__must_report_the_orphan_packages_as_removed(self, simple_process: Mock,
                                                                   process_handler: Mock):
        output = ('The following list of packages will be removed\n'
                  'in the order they are listed:\n'
                  'discord libayatana-appindicator\n'
                  'Do you want to continue ? (yes/no)yes\n'
                  'Removed discord\n'
                  'Removed libayatana-appindicator\n')
        process_handler.return_value.handle_simple.return_value = (True, output)
        self.manager._read_installed_index = Mock(return_value={})

        result = self.manager.uninstall(EopkgPackage(name='discord'), None, Mock())

        self.assertEqual(['discord', 'libayatana-appindicator'],
                         [p.name for p in result.removed])

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_upgrade__must_run_a_single_transaction(self, simple_process: Mock,
                                                    process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')
        requirements = Mock()
        requirements.to_upgrade = [Mock(pkg=EopkgPackage(name='a')),
                                   Mock(pkg=EopkgPackage(name='b'))]

        self.assertTrue(self.manager.upgrade(requirements, 'secret', Mock()))

        self.assertEqual(1, simple_process.call_count)
        self.assertEqual(['eopkg', 'up', '--no-color', '-y', 'a', 'b'],
                         simple_process.call_args[0][0])

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_upgrade__must_sync_repositories_first_when_configured(self, simple_process: Mock,
                                                                   process_handler: Mock):
        self.manager.configman.get_config.return_value['sync_repos_before_upgrade'] = True
        process_handler.return_value.handle_simple.return_value = (True, '')
        requirements = Mock()
        requirements.to_upgrade = [Mock(pkg=EopkgPackage(name='a'))]

        self.manager.upgrade(requirements, 'secret', Mock())

        called = [call[0][0] for call in simple_process.call_args_list]
        self.assertEqual([['eopkg', 'ur', '--no-color'],
                          ['eopkg', 'up', '--no-color', '-y', 'a']], called)

    def test_requires_root__install_uninstall_and_upgrade(self):
        for action in (SoftwareAction.INSTALL, SoftwareAction.UNINSTALL,
                       SoftwareAction.UPGRADE):
            self.assertTrue(self.manager.requires_root(action, EopkgPackage(name='x')))

        self.assertFalse(self.manager.requires_root(SoftwareAction.SEARCH,
                                                    EopkgPackage(name='x')))

    def test_search__must_respect_the_configured_limit(self):
        output = '\n'.join(f'pkg{i} - summary {i}' for i in range(10))
        self.manager._execute_eopkg = Mock(return_value=(True, output))
        self.manager._read_installed_index = Mock(return_value={})
        self.manager._read_upgradable = Mock(return_value=[])
        self.manager.configman.get_config.return_value['search_limit'] = 3

        result = self.manager.search('pkg')

        self.assertEqual(3, result.total)

    def test_search__must_mark_installed_packages_with_a_pending_update(self):
        self.manager._execute_eopkg = Mock(return_value=(True, 'vlc - a player\n'))
        self.manager._read_installed_index = Mock(
            return_value={'vlc': {'name': 'vlc', 'version': '3.0.20', 'release': '78',
                                  'summary': 'a player'}})
        self.manager._read_upgradable = Mock(return_value=['vlc'])

        result = self.manager.search('vlc')

        self.assertEqual(1, len(result.installed))
        self.assertEqual('3.0.20-78', result.installed[0].version)
        self.assertTrue(result.installed[0].update)

    def test_read_installed__must_fill_version_and_update_flag(self):
        self.manager._read_installed_index = Mock(
            return_value={'vlc': {'name': 'vlc', 'version': '3.0.20', 'release': '78',
                                  'summary': 'a player'},
                          'a2ps': {'name': 'a2ps', 'version': '4.14', 'release': '1',
                                   'summary': 'filter'}})
        self.manager._read_upgradable = Mock(return_value=['vlc'])
        self.manager._read_info_index = Mock(return_value={
            'vlc': {'repository': {'version': '3.0.21', 'release': '79'}}})

        result = self.manager.read_installed()
        by_name = {p.name: p for p in result.installed}

        self.assertEqual('3.0.20-78', by_name['vlc'].version)
        self.assertEqual('3.0.21-79', by_name['vlc'].latest_version)
        self.assertTrue(by_name['vlc'].update)
        self.assertFalse(by_name['a2ps'].update)
        self.assertEqual('4.14-1', by_name['a2ps'].version)

    def test_list_updates__must_be_empty_when_there_is_nothing_to_upgrade(self):
        self.manager._execute_eopkg = Mock(return_value=(True, 'No packages to upgrade.\n'))

        self.assertEqual([], self.manager.list_updates(internet_available=True))

    def test_list_updates__must_not_report_a_package_called_no(self):
        self.manager._execute_eopkg = Mock(return_value=(True, 'No packages to upgrade.\n'))

        self.assertEqual([], [u.name for u in self.manager.list_updates(True)])

    def test_list_updates__must_report_the_upgradable_packages(self):
        self.manager._read_upgradable = Mock(return_value=['vlc'])
        self.manager._read_info_index = Mock(return_value={
            'vlc': {'repository': {'version': '3.0.21', 'release': '79'}}})

        updates = self.manager.list_updates(internet_available=True)

        self.assertEqual(1, len(updates))
        self.assertEqual('vlc', updates[0].name)
        self.assertEqual('3.0.21-79', updates[0].version)
        self.assertEqual('eopkg', updates[0].type)

    def test_installed_cache__must_not_relist_on_every_search(self):
        outputs = {'li': 'vlc - a player\n', 'list-upgrades': 'No packages to upgrade.\n',
                   'sr': 'vlc - a player\n'}

        def fake_execute(cmd):
            return True, outputs.get(cmd[1], '')

        self.manager._execute_eopkg = Mock(side_effect=fake_execute)

        self.manager.search('vlc')
        first_call_count = self.manager._execute_eopkg.call_count
        self.manager.search('vlc')

        # la segunda búsqueda sólo vuelve a lanzar 'eopkg sr'
        self.assertEqual(first_call_count + 1, self.manager._execute_eopkg.call_count)

    def test_installed_cache__must_be_invalidated_after_a_transaction(self):
        self.manager._installed_index = {'vlc': {}}
        self.manager._upgradable_names = ['vlc']

        self.manager._invalidate_installed_cache()

        self.assertIsNone(self.manager._installed_index)
        self.assertIsNone(self.manager._upgradable_names)

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_install__must_invalidate_the_installed_cache(self, simple_process: Mock,
                                                          process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')
        self.manager._upgradable_names = ['vlc']
        self.manager._read_installed_index = Mock(return_value={})

        self.manager.install(EopkgPackage(name='vlc'), 'secret', None, Mock())

        self.assertIsNone(self.manager._upgradable_names)

    def test_execute_eopkg__must_force_the_c_locale(self):
        from bauh.gems.eopkg.controller import EOPKG_ENV

        self.assertEqual('C.UTF-8', EOPKG_ENV['LANG'])
        self.assertEqual('C.UTF-8', EOPKG_ENV['LC_ALL'])

    @patch('bauh.gems.eopkg.controller.subprocess.run')
    def test_execute_eopkg__must_pass_a_timeout(self, run: Mock):
        run.return_value = Mock(returncode=0, stdout='', stderr='')

        self.manager._execute_eopkg(['eopkg', 'li'])

        self.assertEqual(60, run.call_args[1]['timeout'])

    @patch('bauh.gems.eopkg.controller.subprocess.run')
    def test_execute_eopkg__must_log_stderr_on_failure(self, run: Mock):
        run.return_value = Mock(returncode=1, stdout='', stderr='database is locked')

        success, _ = self.manager._execute_eopkg(['eopkg', 'li'])

        self.assertFalse(success)
        self.manager.logger.warning.assert_called()


class EopkgManagerSettingsTest(unittest.TestCase):

    def setUp(self):
        self.manager = EopkgManager(Mock())
        self.manager.i18n = _DummyI18n()
        self.manager.configman = Mock()
        self.manager.configman.get_config.return_value = {'search_limit': 50,
                                                          'command_timeout': 60,
                                                          'sync_repos_before_upgrade': True}

    def test_get_settings__must_expose_the_editable_options(self):
        views = list(self.manager.get_settings())

        self.assertEqual(1, len(views))
        form = views[0].component.get_component_by_idx(0, FormComponent)
        self.assertIsNotNone(form.get_component('search_limit'))
        self.assertIsNotNone(form.get_component('command_timeout'))

    def test_save_settings__must_persist_the_values(self):
        views = list(self.manager.get_settings())
        form = views[0].component.get_component_by_idx(0, FormComponent)
        form.get_component('search_limit').set_value('12')
        form.get_component('command_timeout').set_value('90')

        saved, errors = self.manager.save_settings(views[0].component)

        self.assertTrue(saved)
        self.assertIsNone(errors)
        config = self.manager.configman.save_config.call_args[0][0]
        self.assertEqual(12, config['search_limit'])
        self.assertEqual(90, config['command_timeout'])

    def test_save_settings__must_fall_back_on_an_invalid_value(self):
        views = list(self.manager.get_settings())
        form = views[0].component.get_component_by_idx(0, FormComponent)
        form.get_component('search_limit').set_value('not a number')

        self.manager.save_settings(views[0].component)

        config = self.manager.configman.save_config.call_args[0][0]
        self.assertEqual(50, config['search_limit'])

    def test_custom_actions__must_offer_update_repos_and_clean_cache(self):
        actions = list(self.manager.gen_custom_actions())

        self.assertEqual(['update_repositories', 'clean_download_cache'],
                         [a.manager_method for a in actions])
        self.assertTrue(all(a.requires_root for a in actions))

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_update_repositories_action(self, simple_process: Mock, process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')

        self.assertTrue(self.manager.update_repositories('secret', Mock()))
        self.assertEqual(['eopkg', 'ur', '--no-color'], simple_process.call_args[0][0])

    @patch('bauh.gems.eopkg.controller.ProcessHandler')
    @patch('bauh.gems.eopkg.controller.SimpleProcess')
    def test_clean_download_cache_action(self, simple_process: Mock, process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')

        self.assertTrue(self.manager.clean_download_cache('secret', Mock()))
        self.assertEqual(['eopkg', 'dc', '--no-color'], simple_process.call_args[0][0])


class _DummyI18n(dict):
    """i18n mínimo que devuelve la propia clave (con marcadores) para las pruebas."""

    def __getitem__(self, item):
        return f'{item} {{}}' if item.endswith(('installing', 'removing', 'removal_list',
                                                'upgrading_many')) else item

    def get(self, key, default=None):
        return self[key]


if __name__ == '__main__':
    unittest.main()
